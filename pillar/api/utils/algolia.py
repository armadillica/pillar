import logging

from bson import ObjectId
from flask import current_app

from pillar.api.file_storage import generate_link
from . import skip_when_testing

log = logging.getLogger(__name__)

INDEX_ALLOWED_USER_ROLES = {'admin', 'subscriber', 'demo'}
INDEX_ALLOWED_NODE_TYPES = {'asset', 'texture', 'group', 'hdri'}


@skip_when_testing
def algolia_index_user_save(user):
    if 'roles' in user and 'service' in user['roles']:
        return
    # Strip unneeded roles
    if 'roles' in user:
        roles = set(user['roles']).intersection(INDEX_ALLOWED_USER_ROLES)
    else:
        roles = set()
    if current_app.algolia_index_users:
        # Create or update Algolia index for the user
        current_app.algolia_index_users.save_object({
            'objectID': user['_id'],
            'full_name': user['full_name'],
            'username': user['username'],
            'roles': list(roles),
            'groups': user['groups'],
            'email': user['email']
        })


@skip_when_testing
def algolia_index_node_save(node):
    if not current_app.algolia_index_nodes:
        return
    if node['node_type'] not in INDEX_ALLOWED_NODE_TYPES:
        return
    # If a nodes does not have status published, do not index
    if node['properties'].get('status') != 'published':
        return

    projects_collection = current_app.data.driver.db['projects']
    project = projects_collection.find_one({'_id': ObjectId(node['project'])})

    users_collection = current_app.data.driver.db['users']
    user = users_collection.find_one({'_id': ObjectId(node['user'])})

    node_ob = {
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
    }
    if 'description' in node and node['description']:
        node_ob['description'] = node['description']
    if 'picture' in node and node['picture']:
        files_collection = current_app.data.driver.db['files']
        lookup = {'_id': ObjectId(node['picture'])}
        picture = files_collection.find_one(lookup)
        if picture['backend'] == 'gcs':
            variation_t = next((item for item in picture['variations'] \
                                if item['size'] == 't'), None)
            if variation_t:
                node_ob['picture'] = generate_link(picture['backend'],
                                                   variation_t['file_path'], project_id=str(picture['project']),
                                                   is_public=True)
    # If the node has world permissions, compute the Free permission
    if 'permissions' in node and 'world' in node['permissions']:
        if 'GET' in node['permissions']['world']:
            node_ob['is_free'] = True

    # Append the media key if the node is of node_type 'asset'
    if node['node_type'] == 'asset':
        node_ob['media'] = node['properties']['content_type']

    # Add extra properties
    for prop in ('tags', 'license_notes'):
        if prop in node['properties']:
            node_ob[prop] = node['properties'][prop]

    current_app.algolia_index_nodes.save_object(node_ob)


@skip_when_testing
def algolia_index_node_delete(node):
    if current_app.algolia_index_nodes is None:
        return
    current_app.algolia_index_nodes.delete_object(node['_id'])
