import logging

from flask import Blueprint, request, current_app, g
from eve.methods.get import get
from eve.utils import config as eve_config

from application import utils
from application.utils.authorization import require_login

TEXTURE_LIBRARY_QUERY_ARGS = {
    eve_config.QUERY_PROJECTION: utils.dumps({
        'name': 1,
        'url': 1,
        'permissions': 1,
    }),
    eve_config.QUERY_SORT: utils.dumps([('name', 1)]),
    'max_results': 'null',  # this needs to be there, or we get a KeyError.
}

blueprint = Blueprint('blender_cloud', __name__)
log = logging.getLogger(__name__)


@blueprint.route('/texture-libraries')
@require_login()
def texture_libraries():
    # Use Eve method so that we get filtering on permissions for free.
    # This gives all the projects that contain the required node types.
    request.args = TEXTURE_LIBRARY_QUERY_ARGS
    groups = g.current_user['groups']

    result, _, _, status, headers = get(
        'projects',
        {'$or': [
            {'permissions.groups.group': {'$in': groups}},
            {'permissions.world': 'GET'}
        ]})

    if status == 200:
        # Filter those projects that don't contain a top-level texture or group_texture node.
        result['_items'] = [proj for proj in result['_items']
                            if has_texture_node(proj)]

    resp = utils.jsonify(result)
    resp.headers.extend(headers)
    return resp, status


def has_texture_node(proj):
    """Returns True iff the project has a top-level (group)texture node."""

    nodes_collection = current_app.data.driver.db['nodes']

    count = nodes_collection.count(
        {'node_type': 'group_texture',
         'project': proj['_id'],
         'parent': None})
    return count > 0


def setup_app(app, url_prefix):
    app.register_blueprint(blueprint, url_prefix=url_prefix)
