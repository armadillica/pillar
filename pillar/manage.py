from __future__ import division
import os
from bson.objectid import ObjectId
from eve.methods.put import put_internal
from eve.methods.post import post_internal
from flask.ext.script import Manager
from application import app
from manage.node_types.act import node_type_act
from manage.node_types.asset import node_type_asset
from manage.node_types.blog import node_type_blog
from manage.node_types.comment import node_type_comment
from manage.node_types.group import node_type_group
from manage.node_types.post import node_type_post
from manage.node_types.project import node_type_project
from manage.node_types.scene import node_type_scene
from manage.node_types.shot import node_type_shot
from manage.node_types.storage import node_type_storage
from manage.node_types.task import node_type_task
from manage.node_types.texture import node_type_texture
from manage.node_types.group_texture import node_type_group_texture

manager = Manager(app)

MONGO_HOST = os.environ.get('MONGO_HOST', 'localhost')

@manager.command
def runserver():
    try:
        import config
        PORT = config.Development.PORT
        HOST = config.Development.HOST
        DEBUG = config.Development.DEBUG
        app.config['STORAGE_DIR'] = config.Development.STORAGE_DIR
    except ImportError:
        # Default settings
        PORT = 5000
        HOST = '0.0.0.0'
        DEBUG = True
        app.config['STORAGE_DIR'] = '{0}/application/static/storage'.format(
            os.path.dirname(os.path.realpath(__file__)))

    # Automatic creation of STORAGE_DIR path if it's missing
    if not os.path.exists(app.config['STORAGE_DIR']):
        os.makedirs(app.config['STORAGE_DIR'])

    app.run(
        port=PORT,
        host=HOST,
        debug=DEBUG)


def post_item(entry, data):
    return post_internal(entry, data)


def put_item(collection, item):
    item_id = item['_id']
    internal_fields = ['_id', '_etag', '_updated', '_created']
    for field in internal_fields:
        item.pop(field, None)
    # print item
    # print type(item_id)
    p = put_internal(collection, item, **{'_id': item_id})
    if p[0]['_status'] == 'ERR':
        print(p)
        print(item)


@manager.command
def setup_db():
    """Setup the database
    - Create admin, subscriber and demo Group collection
    - Create admin user (must use valid blender-id credentials)
    - Create one project
    """
    # groups_collection = app.data.driver.db['groups']
    groups_list = []
    for group in ['admin', 'subscriber', 'demo']:
        g = {'name': group}
        g = post_internal('groups', g)
        groups_list.append(g[0]['_id'])
        print("Creating group {0}".format(group))

    while True:
        admin_username = raw_input('Admin email:')
        if len(admin_username) < 1:
            print ("Username is too short")
        else:
            break

    user = dict(
        username=admin_username,
        groups=groups_list,
        roles=['admin', 'subscriber', 'demo'],
        settings=dict(email_communications=1),
        auth=[],
        full_name=admin_username,
        email=admin_username,
        )
    user = post_internal('users', user)
    print("Created user {0}".format(user[0]['_id']))

    # TODO: Create a default project

@manager.command
def clear_db():
    """Wipes the database
    """
    from pymongo import MongoClient

    client = MongoClient(MONGO_HOST, 27017)
    db = client.eve
    db.drop_collection('nodes')
    db.drop_collection('node_types')
    db.drop_collection('tokens')
    db.drop_collection('users')


@manager.command
def upgrade_node_types():
    """Wipes node_types collection and populates it again"""
    node_types_collection = app.data.driver.db['node_types']
    node_types = node_types_collection.find({})
    old_ids = {}
    for node_type in node_types:
        old_ids[node_type['name']] = node_type['_id']
    populate_node_types(old_ids)


@manager.command
def manage_groups():
    """Take user email and group name,
    and add or remove the user from that group.
    """
    from pymongo import MongoClient
    client = MongoClient(MONGO_HOST, 27017)
    db = client.eve

    print ("")
    print ("Add or Remove user from group")
    print ("leave empty to cancel")
    print ("")

    # Select Action
    print ("Do you want to Add or Remove the user from the group?")
    retry = True
    while retry:
        action = raw_input('add/remove: ')
        if action == '':
            return
        elif action.lower() in ['add', 'a', 'insert']:
            action == 'add'
            retry = False
        elif action.lower() in ['remove', 'r', 'rmv', 'rem', 'delete', 'del']:
            action = 'remove'
            retry = False
        else:
            print ("Incorrect action, press type 'add' or 'remove'")

    # Select User
    retry = True
    while retry:
        user_email = raw_input('User email: ')
        if user_email == '':
            return
        user = db.users.find_one({'email': user_email})
        if user:
            retry = False
        else:
            print ("Incorrect user email, try again, or leave empty to cancel")

    # Select group
    retry = True
    while retry:
        group_name = raw_input('Group name: ')
        if group_name == '':
            return
        group = db.groups.find_one({'name': group_name})
        if group:
            retry = False
        else:
            print ("Incorrect group name, try again, or leave empty to cancel")

    # Do
    current_groups = user.get('groups', [])
    if action == 'add':
        if group['_id'] in current_groups:
            print "User {0} is already in group {1}".format(
                user_email, group_name)
        else:
            current_groups.append(group['_id'])
            db.users.update({'_id': user['_id']},
                            {"$set": {'groups': current_groups}})
            print "User {0} added to group {1}".format(user_email, group_name)
    elif action == 'remove':
        if group['_id'] not in current_groups:
            print "User {0} is not in group {1}".format(user_email, group_name)
        else:
            current_groups.remove(group['_id'])
            db.users.update({'_id': user['_id']},
                            {"$set": {'groups': current_groups}})
            print "User {0} removed from group {1}".format(
                user_email, group_name)


def populate_node_types(old_ids={}):
    node_types_collection = app.data.driver.db['node_types']

    def mix_node_type(old_id, node_type_dict):
        # Take eve parameters
        node_type = node_types_collection.find_one({'_id': old_id})
        for attr in node_type:
            if attr[0] == '_':
                # Mix with node eve attributes. This is really not needed since
                # the attributes are stripped before doing a put_internal.
                node_type_dict[attr] = node_type[attr]
            elif attr == 'permissions':
                node_type_dict['permissions'] = node_type['permissions']
        return node_type_dict

    def upgrade(node_type, old_ids):
        print("Node {0}".format(node_type['name']))
        node_name = node_type['name']
        if node_name in old_ids:
            node_id = old_ids[node_name]
            node_type = mix_node_type(node_id, node_type)

            # Removed internal fields that would cause validation error
            internal_fields = ['_id', '_etag', '_updated', '_created']
            for field in internal_fields:
                node_type.pop(field, None)
            p = put_internal('node_types', node_type, **{'_id': node_id})
        else:
            print("Making the node")
            print(node_type)
            post_item('node_types', node_type)

    # upgrade(shot_node_type, old_ids)
    # upgrade(task_node_type, old_ids)
    # upgrade(scene_node_type, old_ids)
    # upgrade(act_node_type, old_ids)
    upgrade(node_type_project, old_ids)
    upgrade(node_type_group, old_ids)
    upgrade(node_type_asset, old_ids)
    upgrade(node_type_storage, old_ids)
    upgrade(node_type_comment, old_ids)
    upgrade(node_type_blog, old_ids)
    upgrade(node_type_post, old_ids)
    upgrade(node_type_texture, old_ids)
    upgrade(node_type_group_texture, old_ids)


@manager.command
def add_parent_to_nodes():
    """Find the parent of any node in the nodes collection"""
    import codecs
    import sys

    UTF8Writer = codecs.getwriter('utf8')
    sys.stdout = UTF8Writer(sys.stdout)

    nodes_collection = app.data.driver.db['nodes']
    def find_parent_project(node):
        if node and 'parent' in node:
            parent = nodes_collection.find_one({'_id': node['parent']})
            return find_parent_project(parent)
        if node:
            return node
        else:
            return None
    nodes = nodes_collection.find()
    nodes_index = 0
    nodes_orphan = 0
    for node in nodes:
        nodes_index += 1
        if node['node_type'] == ObjectId("55a615cfea893bd7d0489f2d"):
            print u"Skipping project node - {0}".format(node['name'])
        else:
            project = find_parent_project(node)
            if project:
                nodes_collection.update({'_id': node['_id']},
                                {"$set": {'project': project['_id']}})
                print u"{0} {1}".format(node['_id'], node['name'])
            else:
                nodes_orphan += 1
                nodes_collection.remove({'_id': node['_id']})
                print "Removed {0} {1}".format(node['_id'], node['name'])

    print "Edited {0} nodes".format(nodes_index)
    print "Orphan {0} nodes".format(nodes_orphan)


@manager.command
def remove_children_files():
    """Remove any file object with a parent field"""
    files_collection = app.data.driver.db['files']
    for f in files_collection.find():
        if 'parent' in f:
            file_id = f['_id']
            # Delete child object
            files_collection.remove({'_id': file_id})
            print "deleted {0}".format(file_id)


@manager.command
def make_project_public(project_id):
    """Convert every node of a project from pending to public"""

    DRY_RUN = False
    nodes_collection = app.data.driver.db['nodes']
    for n in nodes_collection.find({'project': ObjectId(project_id)}):
        n['properties']['status'] = 'published'
        print u"Publishing {0} {1}".format(n['_id'], n['name'].encode('ascii', 'ignore'))
        if not DRY_RUN:
            put_item('nodes', n)


@manager.command
def convert_assets_to_textures(project_id):
    """Get any node of type asset in a certain project and convert it to a
    node_type texture.
    """

    DRY_RUN = False

    node_types_collection = app.data.driver.db['node_types']
    files_collection = app.data.driver.db['files']
    nodes_collection = app.data.driver.db['nodes']

    def parse_name(name):
        """Parse a texture name to infer properties"""
        variation = 'col'
        is_tileable = False
        variations = ['_bump', '_spec', '_nor', '_col', '_translucency']
        for v in variations:
            if v in name:
                variation = v[1:]
                break
        if '_tileable' in name:
            is_tileable = True
        return dict(variation=variation, is_tileable=is_tileable)

    def make_texture_node(base_node, files, parent_id=None):
        texture_node_type = node_types_collection.find_one({'name':'texture'})
        files_list = []
        is_tileable = False

        if parent_id is None:
            parent_id = base_node['parent']
        else:
            print "Using provided parent {0}".format(parent_id)

        # Create a list with all the file fariations for the texture
        for f in files:
            print "Processing {1} {0}".format(f['name'], f['_id'])
            attributes = parse_name(f['name'])
            if attributes['is_tileable']:
                is_tileable = True
            file_entry = dict(
                file=f['properties']['file'],
                is_tileable=attributes['is_tileable'],
                map_type=attributes['variation'])
            files_list.append(file_entry)
        # Get the first file from the files list and use it as base for some
        # node properties
        first_file = files_collection.find_one({'_id': files[0]['properties']['file']})
        if 'picture' in base_node and base_node['picture'] != None:
            picture = base_node['picture']
        else:
            picture = first_file['_id']
        if 'height' in first_file:
            node = dict(
                name=base_node['name'],
                picture=picture,
                parent=parent_id,
                project=base_node['project'],
                user=base_node['user'],
                node_type=texture_node_type['_id'],
                properties=dict(
                    status=base_node['properties']['status'],
                    files=files_list,
                    resolution="{0}x{1}".format(first_file['height'], first_file['width']),
                    is_tileable=is_tileable,
                    is_landscape=(first_file['height'] < first_file['width']),
                    aspect_ratio=round(
                        (first_file['width'] / first_file['height']), 2)
                    )
                )
            print "Making {0}".format(node['name'])
            if not DRY_RUN:
                p = post_internal('nodes', node)
                if p[0]['_status'] == 'ERR':
                    import pprint
                    pprint.pprint(node)


    nodes_collection = app.data.driver.db['nodes']

    for n in nodes_collection.find({'project': ObjectId(project_id)}):
        n_type = node_types_collection.find_one({'_id': n['node_type']})
        processed_nodes = []
        if n_type['name'] == 'group' and n['name'].startswith('_'):
            print "Processing {0}".format(n['name'])
            # Get the content of the group
            children = [c for c in nodes_collection.find({'parent': n['_id']})]
            make_texture_node(children[0], children, parent_id=n['parent'])
            processed_nodes += children
            processed_nodes.append(n)
        elif n_type['name'] == 'group':
            # Change group type to texture group
            node_type_texture = node_types_collection.find_one(
                {'name':'group_texture'})
            n['node_type'] = node_type_texture['_id']
            n['properties'].pop('notes', None)
            print "Updating {0}".format(n['name'])
            if not DRY_RUN:
                put_item('nodes', n)
        # Delete processed nodes
        for node in processed_nodes:
            print "Removing {0} {1}".format(node['_id'], node['name'])
            if not DRY_RUN:
                nodes_collection.remove({'_id': node['_id']})
    # Make texture out of single image
    for n in nodes_collection.find({'project': ObjectId(project_id)}):
        n_type = node_types_collection.find_one({'_id': n['node_type']})
        if n_type['name'] == 'asset':
            make_texture_node(n, [n])
            # Delete processed nodes
            print "Removing {0} {1}".format(n['_id'], n['name'])
            if not DRY_RUN:
                nodes_collection.remove({'_id': n['_id']})


@manager.command
def set_attachment_names():
    """Loop through all existing nodes and assign proper ContentDisposition
    metadata to referenced files that are using GCS.
    """
    from application import update_file_name
    nodes_collection = app.data.driver.db['nodes']
    for n in nodes_collection.find():
        print "Updating node {0}".format(n['_id'])
        update_file_name(n)


@manager.command
def files_verify_project():
    """Verify for missing or conflicting node/file ids"""
    nodes_collection = app.data.driver.db['nodes']
    files_collection = app.data.driver.db['files']
    issues = dict(missing=[], conflicting=[], processing=[])

    def _parse_file(item, file_id):
        f = files_collection.find_one({'_id': file_id})
        if f:
            if 'project' in item and 'project' in f:
                if item['project'] != f['project']:
                    issues['conflicting'].append(item['_id'])
                if 'status' in item['properties'] \
                    and item['properties']['status'] == 'processing':
                    issues['processing'].append(item['_id'])
        else:
            issues['missing'].append(
                "{0} missing {1}".format(item['_id'], file_id))

    for item in nodes_collection.find():
        print "Verifying node {0}".format(item['_id'])
        if 'file' in item['properties']:
            _parse_file(item, item['properties']['file'])
        elif 'files' in item['properties']:
            for f in item['properties']['files']:
                _parse_file(item, f['file'])

    print "==="
    print "Issues detected:"
    for k, v in issues.iteritems():
        print "{0}:".format(k)
        for i in v:
            print i
        print "==="


def replace_node_type(project, node_type_name, new_node_type):
    """Update or create the specified node type. We rely on the fact that
    node_types have a unique name in a project.
    """

    old_node_type = next(
        (item for item in project['node_types'] if item.get('name') \
            and item['name'] == node_type_name), None)
    if old_node_type:
        for i, v in enumerate(project['node_types']):
            if v['name'] == node_type_name:
                project['node_types'][i] = new_node_type
    else:
        project['node_types'].append(new_node_type)


@manager.command
def project_upgrade_node_types(project_id):
    projects_collection = app.data.driver.db['projects']
    project = projects_collection.find_one({'_id': ObjectId(project_id)})
    replace_node_type(project, 'group', node_type_group)
    replace_node_type(project, 'asset', node_type_asset)
    replace_node_type(project, 'storage', node_type_storage)
    replace_node_type(project, 'comment', node_type_comment)
    replace_node_type(project, 'blog', node_type_blog)
    replace_node_type(project, 'post', node_type_post)
    replace_node_type(project, 'texture', node_type_texture)
    put_item('projects', project)


@manager.command
def test_put_item(node_id):
    import pprint
    nodes_collection = app.data.driver.db['nodes']
    node = nodes_collection.find_one(ObjectId(node_id))
    pprint.pprint(node)
    put_item('nodes', node)


@manager.command
def test_post_internal(node_id):
    import pprint
    nodes_collection = app.data.driver.db['nodes']
    node = nodes_collection.find_one(ObjectId(node_id))
    internal_fields = ['_id', '_etag', '_updated', '_created']
    for field in internal_fields:
        node.pop(field, None)
    pprint.pprint(node)
    print post_internal('nodes', node)


@manager.command
def algolia_push_users():
    """Loop through all users and push them to Algolia"""
    from application.utils.algolia import algolia_index_user_save
    users_collection = app.data.driver.db['users']
    for user in users_collection.find():
        print "Pushing {0}".format(user['username'])
        algolia_index_user_save(user)


@manager.command
def algolia_push_nodes():
    """Loop through all nodes and push them to Algolia"""
    from application.utils.algolia import algolia_index_node_save
    nodes_collection = app.data.driver.db['nodes']
    for node in nodes_collection.find():
        print u"Pushing {0}: {1}".format(node['_id'], node['name'].encode(
            'ascii', 'ignore'))
        algolia_index_node_save(node)


@manager.command
def files_make_public_t():
    """Loop through all files and if they are images on GCS, make the size t
    public
    """
    from gcloud.exceptions import InternalServerError
    from application.utils.gcs import GoogleCloudStorageBucket
    files_collection = app.data.driver.db['files']
    for f in files_collection.find({'backend': 'gcs'}):
        if 'variations' in f:
            variation_t = next((item for item in f['variations'] \
                if item['size'] == 't'), None)
            if variation_t:
                storage = GoogleCloudStorageBucket(str(f['project']))
                blob = storage.Get(variation_t['file_path'], to_dict=False)
                if blob:
                    try:
                        print("Making blob public: {0}".format(blob.path))
                        blob.make_public()
                    except InternalServerError:
                        print("Internal Server Error")
                    except Exception:
                        pass


if __name__ == '__main__':
    manager.run()
