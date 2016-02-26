from bson import ObjectId
from application import app
from application import algolia_index_users
from application import algolia_index_nodes
from application.modules.file_storage import generate_link

def algolia_index_user_save(user):
    # Define accepted roles
    accepted_roles = ['admin', 'subscriber', 'demo']
    # Strip unneeded roles
    if 'roles' in user:
        roles = [r for r in user['roles'] if r in accepted_roles]
    else:
        roles = None
    if algolia_index_users:
        # Create or update Algolia index for the user
        algolia_index_users.save_object({
            'objectID': user['_id'],
            'full_name': user['full_name'],
            'username': user['username'],
            'roles': roles,
            'groups': user['groups'],
            'email': user['email']
        })


def algolia_index_node_save(node):
    accepted_node_types = ['asset', 'texture', 'group']
    if node['node_type'] in accepted_node_types and algolia_index_nodes:
        projects_collection = app.data.driver.db['projects']
        lookup = {'_id': ObjectId(node['project'])}
        project = projects_collection.find_one(lookup)

        node_ob = {
            'objectID': node['_id'],
            'name': node['name'],
            'project': {
                '_id': project['_id'],
                'name': project['name']
                },
            }
        if 'description' in node and node['description']:
            node_ob['description'] = node['description']
        if 'picture' in node and node['picture']:
            files_collection = app.data.driver.db['files']
            lookup = {'_id': ObjectId(node['picture'])}
            picture = files_collection.find_one(lookup)
            variation_t = next((item for item in picture['variations'] \
                if item['size'] == 't'), None)
            if variation_t:
                node_ob['picture'] = generate_link(picture['backend'],
                    variation_t['file_path'], project_id=str(picture['project']),
                    is_public=True)

        algolia_index_nodes.save_object(node_ob)
