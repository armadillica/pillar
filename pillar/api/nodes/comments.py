import logging
from datetime import datetime

import pymongo
import typing

import bson
import attr
import werkzeug.exceptions as wz_exceptions

import pillar
from pillar import current_app, shortcodes
from pillar.api.nodes.custom.comment import patch_comment
from pillar.api.utils import jsonify, gravatar
from pillar.auth import current_user


log = logging.getLogger(__name__)


@attr.s(auto_attribs=True)
class UserDO:
    id: str
    full_name: str
    gravatar: str
    badges_html: str


@attr.s(auto_attribs=True)
class CommentPropertiesDO:
    attachments: typing.Dict
    rating_positive: int = 0
    rating_negative: int = 0


@attr.s(auto_attribs=True)
class CommentDO:
    id: bson.ObjectId
    parent: bson.ObjectId
    project: bson.ObjectId
    user: UserDO
    msg_html: str
    msg_markdown: str
    properties: CommentPropertiesDO
    created: datetime
    updated: datetime
    etag: str
    replies: typing.List['CommentDO'] = []
    current_user_rating: typing.Optional[bool] = None


@attr.s(auto_attribs=True)
class CommentTreeDO:
    node_id: bson.ObjectId
    project: bson.ObjectId
    nbr_of_comments: int = 0
    comments: typing.List[CommentDO] = []


def _get_markdowned_html(document: dict, field_name: str) -> str:
    cache_field_name = pillar.markdown.cache_field_name(field_name)
    html = document.get(cache_field_name)
    if html is None:
        markdown_src = document.get(field_name) or ''
        html = pillar.markdown.markdown(markdown_src)
    return html


def jsonify_data_object(data_object: attr):
    return jsonify(
        attr.asdict(data_object,
                    recurse=True)
    )


class CommentTreeBuilder:
    def __init__(self, node_id: bson.ObjectId):
        self.node_id = node_id
        self.nbr_of_Comments: int = 0

    def build(self) -> CommentTreeDO:
        enriched_comments = self.child_comments(self.node_id,
                                                sort={'properties.rating_positive': pymongo.DESCENDING,
                                                      '_created': pymongo.DESCENDING})
        project_id = self.get_project_id()
        return CommentTreeDO(
            node_id=self.node_id,
            project=project_id,
            nbr_of_comments=self.nbr_of_Comments,
            comments=enriched_comments
        )

    def child_comments(self, node_id: bson.ObjectId, sort: dict) -> typing.List[CommentDO]:
        raw_comments = self.mongodb_comments(node_id, sort)
        return [self.enrich(comment) for comment in raw_comments]

    def enrich(self, mongo_comment: dict) -> CommentDO:
        self.nbr_of_Comments += 1
        comment = to_comment_data_object(mongo_comment)
        comment.replies = self.child_comments(mongo_comment['_id'],
                                              sort={'_created': pymongo.ASCENDING})
        return comment

    def get_project_id(self):
        nodes_coll = current_app.db('nodes')
        result = nodes_coll.find_one({'_id': self.node_id})
        return result['project']

    @classmethod
    def mongodb_comments(cls, node_id: bson.ObjectId, sort: dict) -> typing.Iterator:
        nodes_coll = current_app.db('nodes')
        return nodes_coll.aggregate([
            {'$match': {'node_type': 'comment',
                        '_deleted': {'$ne': True},
                        'properties.status': 'published',
                        'parent': node_id}},
            {'$lookup': {"from": "users",
                         "localField": "user",
                         "foreignField": "_id",
                         "as": "user"}},
            {'$unwind': {'path': "$user"}},
            {'$sort': sort},
        ])


def get_node_comments(node_id: bson.ObjectId):
    comments_tree = CommentTreeBuilder(node_id).build()
    return jsonify_data_object(comments_tree)


def post_node_comment(parent_id: bson.ObjectId, markdown_msg: str, attachments: dict):
    parent_node = find_node_or_raise(parent_id,
                                     'User %s tried to update comment with bad parent_id %s',
                                     current_user.objectid,
                                     parent_id)

    is_reply = parent_node['node_type'] == 'comment'
    comment = dict(
        parent=parent_id,
        project=parent_node['project'],
        name='Comment',
        user=current_user.objectid,
        node_type='comment',
        properties=dict(
            content=markdown_msg,
            status='published',
            is_reply=is_reply,
            confidence=0,
            rating_positive=0,
            rating_negative=0,
            attachments=attachments,
        )
    )
    r, _, _, status = current_app.post_internal('nodes', comment)

    if status != 201:
        log.warning('Unable to post comment on %s as %s: %s',
                    parent_id, current_user.objectid, r)
        raise wz_exceptions.InternalServerError('Unable to create comment')

    comment_do = get_comment(parent_id, r['_id'])

    return jsonify_data_object(comment_do), 201


def find_node_or_raise(node_id, *args):
    nodes_coll = current_app.db('nodes')
    node_to_comment = nodes_coll.find_one({
            '_id': node_id,
            '_deleted': {'$ne': True},
    })
    if not node_to_comment:
        log.warning(args)
        raise wz_exceptions.UnprocessableEntity()
    return node_to_comment


def patch_node_comment(parent_id: bson.ObjectId, comment_id: bson.ObjectId, markdown_msg: str, attachments: dict):
    _, _ = find_parent_and_comment_or_raise(parent_id, comment_id)

    patch = dict(
        op='edit',
        content=markdown_msg,
        attachments=attachments
    )

    json_result = patch_comment(comment_id, patch)
    if json_result.json['result'] != 200:
        raise wz_exceptions.InternalServerError('Failed to update comment')

    comment_do = get_comment(parent_id, comment_id)

    return jsonify_data_object(comment_do), 200


def find_parent_and_comment_or_raise(parent_id, comment_id):
    parent = find_node_or_raise(parent_id,
                                'User %s tried to update comment with bad parent_id %s',
                                current_user.objectid,
                                parent_id)
    comment = find_node_or_raise(comment_id,
                                 'User %s tried to update comment with bad id %s',
                                 current_user.objectid,
                                 comment_id)
    validate_comment_parent_relation(comment, parent)
    return parent, comment


def validate_comment_parent_relation(comment, parent):
    if comment['parent'] != parent['_id']:
        log.warning('User %s tried to update comment with bad parent/comment pair. parent_id: %s comment_id: %s',
                    current_user.objectid,
                    parent['_id'],
                    comment['_id'])
        raise wz_exceptions.BadRequest()


def get_comment(parent_id: bson.ObjectId, comment_id: bson.ObjectId) -> CommentDO:
    nodes_coll = current_app.db('nodes')
    mongo_comment = list(nodes_coll.aggregate([
        {'$match': {'node_type': 'comment',
                    '_deleted': {'$ne': True},
                    'properties.status': 'published',
                    'parent': parent_id,
                    '_id': comment_id}},
        {'$lookup': {"from": "users",
                     "localField": "user",
                     "foreignField": "_id",
                     "as": "user"}},
        {'$unwind': {'path': "$user"}},
    ]))[0]

    return to_comment_data_object(mongo_comment)


def to_comment_data_object(mongo_comment: dict) -> CommentDO:
    def current_user_rating():
        if current_user.is_authenticated:
            for rating in mongo_comment['properties'].get('ratings', ()):
                if str(rating['user']) != current_user.objectid:
                    continue
                return rating['is_positive']
        return None

    user_dict = mongo_comment['user']
    user = UserDO(
        id=str(mongo_comment['user']['_id']),
        full_name=user_dict['full_name'],
        gravatar=gravatar(user_dict['email']),
        badges_html=user_dict.get('badges', {}).get('html', '')
    )
    html = _get_markdowned_html(mongo_comment['properties'], 'content')
    html = shortcodes.render_commented(html, context=mongo_comment['properties'])
    return CommentDO(
        id=mongo_comment['_id'],
        parent=mongo_comment['parent'],
        project=mongo_comment['project'],
        user=user,
        msg_html=html,
        msg_markdown=mongo_comment['properties']['content'],
        current_user_rating=current_user_rating(),
        created=mongo_comment['_created'],
        updated=mongo_comment['_updated'],
        etag=mongo_comment['_etag'],
        properties=CommentPropertiesDO(
            attachments=mongo_comment['properties'].get('attachments', {}),
            rating_positive=mongo_comment['properties']['rating_positive'],
            rating_negative=mongo_comment['properties']['rating_negative']
        )
    )


def post_node_comment_vote(parent_id: bson.ObjectId, comment_id: bson.ObjectId, vote: int):
    normalized_vote = min(max(vote, -1), 1)
    _, _ = find_parent_and_comment_or_raise(parent_id, comment_id)

    actions = {
        1: 'upvote',
        0: 'revoke',
        -1: 'downvote',
    }

    patch = dict(
        op=actions[normalized_vote]
    )

    json_result = patch_comment(comment_id, patch)
    if json_result.json['_status'] != 'OK':
        raise wz_exceptions.InternalServerError('Failed to vote on comment')

    comment_do = get_comment(parent_id, comment_id)
    return jsonify_data_object(comment_do), 200
