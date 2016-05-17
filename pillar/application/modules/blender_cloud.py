from flask import Blueprint, request
from eve.methods.get import get
from eve.utils import config as eve_config

from application import utils

TEXTURE_LIBRARY_QUERY_ARGS = {
    eve_config.QUERY_PROJECTION: utils.dumps({
        'name': 1, 'url': 1, 'permissions': 1, 'node_types.name': 1,}),
    eve_config.QUERY_SORT: utils.dumps([('name', 1)]),
    'max_results': 'null',}

blueprint = Blueprint('blender_cloud', __name__)


@blueprint.route('/texture-libraries')
def texture_libraries():
    # Use Eve method so that we get filtering on permissions for free.
    request.args = TEXTURE_LIBRARY_QUERY_ARGS
    projects = get('projects', {'node_types.name': 'texture'})

    return utils.jsonify(projects)


def setup_app(app, url_prefix):
    app.register_blueprint(blueprint, url_prefix=url_prefix)
