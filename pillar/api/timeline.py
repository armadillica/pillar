import itertools
import typing
from datetime import datetime
from operator import itemgetter

import attr
import bson
import pymongo
from flask import Blueprint, current_app, request, url_for

import pillar
from pillar import shortcodes
from pillar.api.utils import jsonify, pretty_duration, str2id

blueprint = Blueprint('timeline', __name__)


@attr.s(auto_attribs=True)
class TimelineDO:
    groups: typing.List['GroupDO'] = []
    continue_from: typing.Optional[float] = None


@attr.s(auto_attribs=True)
class GroupDO:
    label: typing.Optional[str] = None
    url: typing.Optional[str] = None
    items: typing.Dict = {}
    groups: typing.Iterable['GroupDO'] = []


class SearchHelper:
    def __init__(self, nbr_of_weeks: int, continue_from: typing.Optional[datetime],
                 project_ids: typing.List[bson.ObjectId], sort_direction: str):
        self._nbr_of_weeks = nbr_of_weeks
        self._continue_from = continue_from
        self._project_ids = project_ids
        self.sort_direction = sort_direction

    def _match(self, continue_from: typing.Optional[datetime]) -> dict:
        created = {}
        if continue_from:
            if self.sort_direction == 'desc':
                created = {'_created': {'$lt': continue_from}}
            else:
                created = {'_created': {'$gt': continue_from}}
        return {'_deleted': {'$ne': True},
                'node_type': {'$in': ['asset', 'post']},
                'properties.status': {'$eq': 'published'},
                'project': {'$in': self._project_ids},
                **created,
                }

    def raw_weeks_from_mongo(self) -> pymongo.collection.Collection:
        direction = pymongo.DESCENDING if self.sort_direction == 'desc' else pymongo.ASCENDING
        nodes_coll = current_app.db('nodes')
        return nodes_coll.aggregate([
            {'$match': self._match(self._continue_from)},
            {'$lookup': {"from": "projects",
                         "localField": "project",
                         "foreignField": "_id",
                         "as": "project"}},
            {'$unwind': {'path': "$project"}},
            {'$lookup': {"from": "users",
                         "localField": "user",
                         "foreignField": "_id",
                         "as": "user"}},
            {'$unwind': {'path': "$user"}},
            {'$project': {
                '_created': 1,
                'project._id': 1,
                'project.url': 1,
                'project.name': 1,
                'user._id': 1,
                'user.full_name': 1,
                'name': 1,
                'node_type': 1,
                'picture': 1,
                'properties': 1,
                'permissions': 1,
            }},
            {'$group': {
                '_id': {'year': {'$isoWeekYear': '$_created'},
                        'week': {'$isoWeek': '$_created'}},
                'nodes': {'$push': '$$ROOT'}
            }},
            {'$sort': {'_id.year': direction,
                       '_id.week': direction}},
            {'$limit': self._nbr_of_weeks}
        ])

    def has_more(self, continue_from: datetime) -> bool:
        nodes_coll = current_app.db('nodes')
        result = nodes_coll.count(self._match(continue_from))
        return bool(result)


class Grouper:
    @classmethod
    def label(cls, node):
        return None

    @classmethod
    def url(cls, node):
        return None

    @classmethod
    def group_key(cls) -> typing.Callable[[dict], typing.Any]:
        raise NotImplemented()

    @classmethod
    def sort_key(cls) -> typing.Callable[[dict], typing.Any]:
        raise NotImplemented()


class ProjectGrouper(Grouper):
    @classmethod
    def label(cls, project: dict):
        return project['name']

    @classmethod
    def url(cls, project: dict):
        return url_for('projects.view', project_url=project['url'])

    @classmethod
    def group_key(cls) -> typing.Callable[[dict], typing.Any]:
        return itemgetter('project')

    @classmethod
    def sort_key(cls) -> typing.Callable[[dict], typing.Any]:
        return lambda node: node['project']['_id']


class UserGrouper(Grouper):
    @classmethod
    def label(cls, user):
        return user['full_name']

    @classmethod
    def group_key(cls) -> typing.Callable[[dict], typing.Any]:
        return itemgetter('user')

    @classmethod
    def sort_key(cls) -> typing.Callable[[dict], typing.Any]:
        return lambda node: node['user']['_id']


class TimeLineBuilder:
    def __init__(self, search_helper: SearchHelper, grouper: typing.Type[Grouper]):
        self.search_helper = search_helper
        self.grouper = grouper
        self.continue_from = None

    def build(self) -> TimelineDO:
        raw_weeks = self.search_helper.raw_weeks_from_mongo()
        clean_weeks = (self.create_week_group(week) for week in raw_weeks)

        return TimelineDO(
            groups=list(clean_weeks),
            continue_from=self.continue_from.timestamp() if self.search_helper.has_more(self.continue_from) else None
        )

    def create_week_group(self, week: dict) -> GroupDO:
        nodes = week['nodes']
        nodes.sort(key=itemgetter('_created'), reverse=True)
        self.update_continue_from(nodes)
        groups = self.create_groups(nodes)

        return GroupDO(
            label=f'Week {week["_id"]["week"]}, {week["_id"]["year"]}',
            groups=groups
        )

    def create_groups(self, nodes: typing.List[dict]) -> typing.List[GroupDO]:
        self.sort_nodes(nodes)  # groupby assumes that the list is sorted
        nodes_grouped = itertools.groupby(nodes, self.grouper.group_key())
        groups = (self.clean_group(grouped_by, group) for grouped_by, group in nodes_grouped)
        groups_sorted = sorted(groups, key=self.group_row_sorter, reverse=True)
        return groups_sorted

    def sort_nodes(self, nodes: typing.List[dict]):
        nodes.sort(key=itemgetter('node_type'))
        nodes.sort(key=self.grouper.sort_key())

    def update_continue_from(self, sorted_nodes: typing.List[dict]):
        if self.search_helper.sort_direction == 'desc':
            first_created = sorted_nodes[-1]['_created']
            candidate = self.continue_from or first_created
            self.continue_from = min(candidate, first_created)
        else:
            last_created = sorted_nodes[0]['_created']
            candidate = self.continue_from or last_created
            self.continue_from = max(candidate, last_created)

    def clean_group(self, grouped_by: typing.Any, group: typing.Iterable[dict]) -> GroupDO:
        items = self.create_items(group)
        return GroupDO(
            label=self.grouper.label(grouped_by),
            url=self.grouper.url(grouped_by),
            items=items
        )

    def create_items(self, group) -> typing.List[dict]:
        by_node_type = itertools.groupby(group, key=itemgetter('node_type'))
        items = {}
        for node_type, nodes in by_node_type:
            items[node_type] = [self.node_prettyfy(n) for n in nodes]
        return items

    @classmethod
    def node_prettyfy(cls, node: dict)-> dict:
        duration_seconds = node['properties'].get('duration_seconds')
        if duration_seconds is not None:
            node['properties']['duration'] = pretty_duration(duration_seconds)
        if node['node_type'] == 'post':
            html = _get_markdowned_html(node['properties'], 'content')
            html = shortcodes.render_commented(html, context=node['properties'])
            node['properties']['pretty_content'] = html
        return node

    @classmethod
    def group_row_sorter(cls, row: GroupDO) -> typing.Tuple[datetime, datetime]:
        '''
        If a group contains posts are more interesting and therefor we put them higher in up
        :param row:
        :return: tuple with newest post date and newest asset date
        '''
        def newest_created(nodes: typing.List[dict]) -> datetime:
            if nodes:
                return nodes[0]['_created']
            return datetime.fromtimestamp(0, tz=bson.tz_util.utc)
        newest_post_date = newest_created(row.items.get('post'))
        newest_asset_date = newest_created(row.items.get('asset'))
        return newest_post_date, newest_asset_date


def _public_project_ids() -> typing.List[bson.ObjectId]:
    """Returns a list of ObjectIDs of public projects.

    Memoized in setup_app().
    """

    proj_coll = current_app.db('projects')
    result = proj_coll.find({'is_private': False}, {'_id': 1})
    return [p['_id'] for p in result]


def _get_markdowned_html(document: dict, field_name: str) -> str:
    cache_field_name = pillar.markdown.cache_field_name(field_name)
    html = document.get(cache_field_name)
    if html is None:
        markdown_src = document.get(field_name) or ''
        html = pillar.markdown.markdown(markdown_src)
    return html


@blueprint.route('/', methods=['GET'])
def global_timeline():
    continue_from_str = request.args.get('from')
    continue_from = parse_continue_from(continue_from_str)
    nbr_of_weeks_str = request.args.get('weeksToLoad')
    nbr_of_weeks = parse_nbr_of_weeks(nbr_of_weeks_str)
    sort_direction = request.args.get('dir', 'desc')
    return _global_timeline(continue_from, nbr_of_weeks, sort_direction)


@blueprint.route('/p/<string(length=24):pid_path>', methods=['GET'])
def project_timeline(pid_path: str):
    continue_from_str = request.args.get('from')
    continue_from = parse_continue_from(continue_from_str)
    nbr_of_weeks_str = request.args.get('weeksToLoad')
    nbr_of_weeks = parse_nbr_of_weeks(nbr_of_weeks_str)
    sort_direction = request.args.get('dir', 'desc')
    pid = str2id(pid_path)
    return _project_timeline(continue_from, nbr_of_weeks, sort_direction, pid)


def parse_continue_from(from_arg) -> typing.Optional[datetime]:
    try:
        from_float = float(from_arg)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(from_float, tz=bson.tz_util.utc)


def parse_nbr_of_weeks(weeks_to_load: str) -> int:
    try:
        return int(weeks_to_load)
    except (TypeError, ValueError):
        return 3


def _global_timeline(continue_from: typing.Optional[datetime], nbr_of_weeks: int, sort_direction: str):
    """Returns an aggregated view of what has happened on the site
    Memoized in setup_app().

    :param continue_from: Python utc timestamp where to begin aggregation

    :param nbr_of_weeks: Number of weeks to return

    Example output:
    {
    groups: [{
        label: 'Week 32',
        groups: [{
            label: 'Spring',
            url: '/p/spring',
            items:{
                post: [blogPostDoc, blogPostDoc],
                asset: [assetDoc, assetDoc]
            },
            groups: ...
            }]
        }],
        continue_from: 123456.2 // python timestamp
    }
    """
    builder = TimeLineBuilder(
        SearchHelper(nbr_of_weeks, continue_from, _public_project_ids(), sort_direction),
        ProjectGrouper
    )
    return jsonify_timeline(builder.build())


def jsonify_timeline(timeline: TimelineDO):
    return jsonify(
        attr.asdict(timeline,
                    recurse=True,
                    filter=lambda att, value: value is not None)
    )


def _project_timeline(continue_from: typing.Optional[datetime], nbr_of_weeks: int, sort_direction, pid: bson.ObjectId):
    """Returns an aggregated view of what has happened on the site
    Memoized in setup_app().

    :param continue_from: Python utc timestamp where to begin aggregation

    :param nbr_of_weeks: Number of weeks to return

    Example output:
    {
    groups: [{
        label: 'Week 32',
        groups: [{
            label: 'Tobias Johansson',
            items:{
                post: [blogPostDoc, blogPostDoc],
                asset: [assetDoc, assetDoc]
            },
            groups: ...
            }]
        }],
        continue_from: 123456.2 // python timestamp
    }
    """
    builder = TimeLineBuilder(
        SearchHelper(nbr_of_weeks, continue_from, [pid], sort_direction),
        UserGrouper
    )
    return jsonify_timeline(builder.build())


def setup_app(app, url_prefix):
    global _public_project_ids
    global _global_timeline
    global _project_timeline

    app.register_api_blueprint(blueprint, url_prefix=url_prefix)
    cached = app.cache.cached(timeout=3600)
    _public_project_ids = cached(_public_project_ids)
    memoize = app.cache.memoize(timeout=60)
    _global_timeline = memoize(_global_timeline)
    _project_timeline = memoize(_project_timeline)
