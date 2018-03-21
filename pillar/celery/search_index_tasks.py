import logging
from bson import ObjectId

from pillar import current_app
from pillar.api.file_storage import generate_link
from pillar.api.search import elastic_indexing
from pillar.api.search import algolia_indexing


log = logging.getLogger(__name__)


INDEX_ALLOWED_NODE_TYPES = {'asset', 'texture', 'group', 'hdri'}


SEARCH_BACKENDS = {
    'algolia': algolia_indexing,
    'elastic': elastic_indexing
}


def _get_node_from_id(node_id: str):
    node_oid = ObjectId(node_id)

    nodes_coll = current_app.db('nodes')
    node = nodes_coll.find_one({'_id': node_oid})

    return node


def _handle_picture(node: dict, to_index: dict):
    """Add picture URL in-place to the to-be-indexed node."""

    picture_id = node.get('picture')
    if not picture_id:
        return

    files_collection = current_app.data.driver.db['files']
    lookup = {'_id': ObjectId(picture_id)}
    picture = files_collection.find_one(lookup)

    for item in picture.get('variations', []):
        if item['size'] != 't':
            continue

        # Not all files have a project...
        pid = picture.get('project')
        if pid:
            link = generate_link(picture['backend'],
                                 item['file_path'],
                                 str(pid),
                                 is_public=True)
        else:
            link = item['link']
        to_index['picture'] = link
        break


def prepare_node_data(node_id: str, node: dict=None) -> dict:
    """Given a node id or a node document, return an indexable version of it.

    Returns an empty dict when the node shouldn't be indexed.
    """

    if node_id and node:
        raise ValueError("Do not provide node and node_id together")

    if node_id:
        node = _get_node_from_id(node_id)

    if node is None:
        log.warning('Unable to find node %s, not updating.', node_id)
        return {}

    if node['node_type'] not in INDEX_ALLOWED_NODE_TYPES:
        return {}
    # If a nodes does not have status published, do not index
    if node['properties'].get('status') != 'published':
        return {}

    projects_collection = current_app.data.driver.db['projects']
    project = projects_collection.find_one({'_id': ObjectId(node['project'])})

    users_collection = current_app.data.driver.db['users']
    user = users_collection.find_one({'_id': ObjectId(node['user'])})

    to_index = {
        'objectID': node['_id'],
        'name': node['name'],
        'project': {
            '_id': project['_id'],
            'name': project['name']
        },
        'created': node['_created'],
        'updated': node['_updated'],
        'node_type': node['node_type'],
        'user': {
            '_id': user['_id'],
            'full_name': user['full_name']
        },
        'description': node.get('description'),
    }

    _handle_picture(node, to_index)

    # If the node has world permissions, compute the Free permission
    if 'world' in node.get('permissions', {}):
        if 'GET' in node['permissions']['world']:
            to_index['is_free'] = True

    # Append the media key if the node is of node_type 'asset'
    if node['node_type'] == 'asset':
        to_index['media'] = node['properties']['content_type']

    # Add extra properties
    for prop in ('tags', 'license_notes'):
        if prop in node['properties']:
            to_index[prop] = node['properties'][prop]

    return to_index


def prepare_user_data(user_id: str, user=None) -> dict:
    """
    Prepare data to index for user node.

    Returns an empty dict if the user should not be indexed.
    """

    if not user:
        user_oid = ObjectId(user_id)
        log.info('Retrieving user %s', user_oid)
        users_coll = current_app.db('users')
        user = users_coll.find_one({'_id': user_oid})

    if user is None:
        log.warning('Unable to find user %s, not updating search index.', user_id)
        return {}

    user_roles = set(user.get('roles', ()))

    if 'service' in user_roles:
        return {}

    # Strip unneeded roles
    index_roles = user_roles.intersection(current_app.user_roles_indexable)

    log.debug('Push user %r to Search index', user['_id'])

    user_to_index = {
        'objectID': user['_id'],
        'full_name': user['full_name'],
        'username': user['username'],
        'roles': list(index_roles),
        'groups': user['groups'],
        'email': user['email']
    }

    return user_to_index


@current_app.celery.task(ignore_result=True)
def updated_user(user_id: str):
    """Push an update to the index when a user item is updated"""

    user_to_index = prepare_user_data(user_id)

    for searchoption in current_app.config['SEARCH_BACKENDS']:
        searchmodule = SEARCH_BACKENDS[searchoption]
        searchmodule.push_updated_user(user_to_index)


@current_app.celery.task(ignore_result=True)
def node_save(node_id: str):

    to_index = prepare_node_data(node_id)

    for searchoption in current_app.config['SEARCH_BACKENDS']:
        searchmodule = SEARCH_BACKENDS[searchoption]
        searchmodule.index_node_save(to_index)


@current_app.celery.task(ignore_result=True)
def node_delete(node_id: str):

    # Deleting a node takes nothing more than the ID anyway.
    # No need to fetch anything from Mongo.
    delete_id = ObjectId(node_id)

    for searchoption in current_app.config['SEARCH_BACKENDS']:
        searchmodule = SEARCH_BACKENDS[searchoption]
        searchmodule.index_node_delete(delete_id)
