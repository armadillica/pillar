import functools
import logging

from eve.methods.get import get
from eve.utils import config as eve_config
from flask import Blueprint, request, current_app, g
from pillar.api import utils
from pillar.api.utils.authentication import current_user_id
from pillar.api.utils.authorization import require_login
from werkzeug.datastructures import MultiDict
from werkzeug.exceptions import InternalServerError

FIRST_ADDON_VERSION_WITH_HDRI = (1, 4, 0)
TL_PROJECTION = utils.dumps({'name': 1, 'url': 1, 'permissions': 1,})
TL_SORT = utils.dumps([('name', 1)])

TEXTURE_LIBRARY_QUERY_ARGS = {
    eve_config.QUERY_PROJECTION: TL_PROJECTION,
    eve_config.QUERY_SORT: TL_SORT,
    'max_results': 'null',  # this needs to be there, or we get a KeyError.
}

blueprint = Blueprint('blender_cloud.texture_libs', __name__)
log = logging.getLogger(__name__)


def keep_fetching_texture_libraries(proj_filter):
    groups = g.current_user['groups']
    user_id = g.current_user['user_id']

    page = 1
    max_page = float('inf')

    while page <= max_page:
        request.args.setlist(eve_config.QUERY_PAGE, [page])

        result, _, _, status, _ = get(
            'projects',
            {'$or': [
                {'user': user_id},
                {'permissions.groups.group': {'$in': groups}},
                {'permissions.world': 'GET'}
            ]})

        if status != 200:
            log.warning('Error fetching texture libraries: %s', result)
            raise InternalServerError('Error fetching texture libraries')

        for proj in result['_items']:
            if proj_filter(proj):
                yield proj

        # Compute the last page number we should query.
        meta = result['_meta']
        max_page = meta['total'] // meta['max_results']
        if meta['total'] % meta['max_results'] > 0:
            max_page += 1

        page += 1


@blueprint.route('/texture-libraries')
@require_login()
def texture_libraries():
    from . import blender_cloud_addon_version

    # Use Eve method so that we get filtering on permissions for free.
    # This gives all the projects that contain the required node types.
    request.args = MultiDict(request.args)  # allow changes; it's an ImmutableMultiDict by default.
    request.args.setlist(eve_config.QUERY_PROJECTION, [TL_PROJECTION])
    request.args.setlist(eve_config.QUERY_SORT, [TL_SORT])

    # Determine whether to return HDRi projects too, based on the version
    # of the Blender Cloud Addon. If the addon version is None, we're dealing
    # with a version of the BCA that's so old it doesn't send its version along.
    addon_version = blender_cloud_addon_version()
    return_hdri = addon_version is not None and addon_version >= FIRST_ADDON_VERSION_WITH_HDRI
    log.debug('User %s has Blender Cloud Addon version %s; return_hdri=%s',
              current_user_id(), addon_version, return_hdri)

    accept_as_library = functools.partial(has_texture_node, return_hdri=return_hdri)

    # Construct eve-like response.
    projects = list(keep_fetching_texture_libraries(accept_as_library))
    result = {'_items': projects,
              '_meta': {
                  'max_results': len(projects),
                  'page': 1,
                  'total': len(projects),
              }}

    return utils.jsonify(result)


def has_texture_node(proj, return_hdri=True):
    """Returns True iff the project has a top-level (group)texture node."""

    nodes_collection = current_app.data.driver.db['nodes']

    # See which types of nodes we support.
    node_types = ['group_texture']
    if return_hdri:
        node_types.append('group_hdri')

    count = nodes_collection.count(
        {'node_type': {'$in': node_types},
         'project': proj['_id'],
         'parent': None})
    return count > 0


def sort_by_image_width(node, original=None):
    """Sort the files in an HDRi node by image file size."""

    if node.get('node_type') != 'hdri':
        return

    if not node.get('properties', {}).get('files'):
        return

    # TODO: re-enable this once all current HDRis have been saved in correct order.
    # # Don't bother sorting when the files haven't changed.
    # if original is not None and \
    #                 original.get('properties', {}).get('files') == node['properties']['files']:
    #     return

    log.info('Sorting HDRi node %s', node.get('_id', 'NO-ID'))
    files_coll = current_app.data.driver.db['files']

    def sort_key(file_ref):
        file_doc = files_coll.find_one(file_ref['file'], projection={'length': 1})
        return file_doc['length']

    node['properties']['files'].sort(key=sort_key)


def sort_nodes_by_image_width(nodes):
    for node in nodes:
        sort_by_image_width(node)


def setup_app(app, url_prefix):
    app.on_replace_nodes += sort_by_image_width
    app.on_insert_nodes += sort_nodes_by_image_width

    app.register_api_blueprint(blueprint, url_prefix=url_prefix)
