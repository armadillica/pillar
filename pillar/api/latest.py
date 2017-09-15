import typing

import bson
import pymongo
from flask import Blueprint, current_app

from pillar.api.utils import jsonify

blueprint = Blueprint('latest', __name__)


def _public_project_ids() -> typing.List[bson.ObjectId]:
    """Returns a list of ObjectIDs of public projects.

    Memoized in setup_app().
    """

    proj_coll = current_app.db('projects')
    result = proj_coll.find({'is_private': False}, {'_id': 1})
    return [p['_id'] for p in result]


def latest_nodes(db_filter, projection, limit):
    """Returns the latest nodes, of a certain type, of public projects.

    Also includes information about the project and the user of each node.
    """

    proj = {
        '_created': 1,
        '_updated': 1,
        'user.full_name': 1,
        'project._id': 1,
        'project.url': 1,
        'project.name': 1,
        'name': 1,
        'node_type': 1,
        'parent': 1,
        **projection,
    }

    nodes_coll = current_app.db('nodes')
    pipeline = [
        {'$match': {'_deleted': {'$ne': True}}},
        {'$match': db_filter},
        {'$match': {'project': {'$in': _public_project_ids()}}},
        {'$sort': {'_created': pymongo.DESCENDING}},
        {'$limit': limit},
        {'$lookup': {"from": "users",
                     "localField": "user",
                     "foreignField": "_id",
                     "as": "user"}},
        {'$unwind': {'path': "$user"}},
        {'$lookup': {"from": "projects",
                     "localField": "project",
                     "foreignField": "_id",
                     "as": "project"}},
        {'$unwind': {'path': "$project"}},
        {'$project': proj},
    ]

    latest = nodes_coll.aggregate(pipeline)
    return list(latest)


@blueprint.route('/assets')
def latest_assets():
    latest = latest_nodes({'node_type': 'asset',
                           'properties.status': 'published'},
                          {'name': 1, 'node_type': 1,
                           'parent': 1, 'picture': 1, 'properties.status': 1,
                           'properties.content_type': 1,
                           'permissions.world': 1},
                          12)

    return jsonify({'_items': latest})


@blueprint.route('/comments')
def latest_comments():
    latest = latest_nodes({'node_type': 'comment',
                           'properties.status': 'published'},
                          {'parent': 1,
                           'properties.content': 1, 'node_type': 1,
                           'properties.status': 1,
                           'properties.is_reply': 1},
                          10)

    # Embed the comments' parents.
    # TODO: move to aggregation pipeline.
    nodes = current_app.data.driver.db['nodes']
    parents = {}
    for comment in latest:
        parent_id = comment['parent']

        if parent_id in parents:
            comment['parent'] = parents[parent_id]
            continue

        parent = nodes.find_one(parent_id)
        parents[parent_id] = parent
        comment['parent'] = parent

    return jsonify({'_items': latest})


def setup_app(app, url_prefix):
    global _public_project_ids

    app.register_api_blueprint(blueprint, url_prefix=url_prefix)
    cached = app.cache.cached(timeout=3600)
    _public_project_ids = cached(_public_project_ids)
