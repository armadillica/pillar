import os
from eve.methods.put import put_internal
from flask.ext.script import Manager
from application import app
from application import db
from application import post_item
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


def get_id(collection, name):
    """Returns the _id of the given collection and name"""
    from pymongo import MongoClient
    client = MongoClient(MONGO_HOST, 27017)
    db = client.eve
    node = db[collection].find({'name': name})
    print (node[0]['_id'])
    return node[0]['_id']


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


@manager.command
def add_parent_to_nodes():
    """Find the parent of any node in the nodes collection"""
    import codecs
    import sys
    from bson.objectid import ObjectId
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

if __name__ == '__main__':
    manager.run()
