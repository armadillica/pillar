import os
from application import app
from application import post_item
from flask.ext.script import Manager

manager = Manager(app)

@manager.command
def runserver():
    try:
        import config
        PORT = config.Development.PORT
        HOST = config.Development.HOST
        DEBUG = config.Development.DEBUG
        app.config['FILE_STORAGE'] = config.Development.FILE_STORAGE
    except ImportError:
        # Default settings
        PORT = 5000
        HOST = '0.0.0.0'
        DEBUG = True
        app.config['FILE_STORAGE'] = '{0}/application/static/storage'.format(
            os.path.dirname(os.path.realpath(__file__)))

    # Automatic creation of FILE_STORAGE path if it's missing
    if not os.path.exists(app.config['FILE_STORAGE']):
        os.makedirs(app.config['FILE_STORAGE'])

    app.run(
        port=PORT,
        host=HOST,
        debug=DEBUG)


@manager.command
def clear_db():
    """Wipes the database
    """
    from pymongo import MongoClient

    client = MongoClient()
    db = client.eve
    db.drop_collection('nodes')
    db.drop_collection('node_types')
    db.drop_collection('tokens')
    db.drop_collection('users')


@manager.command
def remove_properties_order():
    """Removes properties.order
    """
    from pymongo import MongoClient
    client = MongoClient()
    db = client.eve
    nodes = db.nodes.find()
    for node in nodes:
        new_prop = {}
        for prop in node['properties']:
            if prop == 'order':
                continue
            else:
                new_prop[prop] = node['properties'][prop]
        db.nodes.update({"_id": node['_id']},
                        {"$set": {"properties": new_prop}})


@manager.command
def upgrade_node_types():
    """Wipes node_types collection
    and populates it again
    """
    from pymongo import MongoClient

    client = MongoClient()
    db = client.eve
    node_types = db.node_types.find({})
    old_ids = {}
    for nt in node_types:
        old_ids[nt['name']] = nt['_id']
    populate_node_types(old_ids)


def get_id(collection, name):
    """Returns the _id of the given collection
    and name."""
    from pymongo import MongoClient
    client = MongoClient()
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
    client = MongoClient()
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


@manager.command
def add_groups():
    """Add permisions
    """
    admin_group = {
        'name': 'admin',
        'permissions': [
            {'node_type': get_id('node_types', 'shot'),
             'permissions': ['GET', 'POST', 'UPDATE', 'DELETE']
             },
            {'node_type': get_id('node_types', 'task'),
             'permissions': ['GET', 'POST', 'UPDATE', 'DELETE']
             },
            {'node_type': get_id('node_types', 'scene'),
             'permissions': ['GET', 'POST', 'UPDATE', 'DELETE']
             },
            {'node_type': get_id('node_types', 'act'),
             'permissions': ['GET', 'POST', 'UPDATE', 'DELETE']
             },
            {'node_type': get_id('node_types', 'comment'),
             'permissions': ['GET', 'POST', 'UPDATE', 'DELETE']
             },
        ]
    }
    post_item('groups', admin_group)

    owner_group = {
        'name': 'owner',
        'permissions': [
            {'node_type': get_id('node_types', 'shot'),
             'permissions': ['GET', 'UPDATE', 'DELETE']
             },
            {'node_type': get_id('node_types', 'task'),
             'permissions': ['GET', 'UPDATE', 'DELETE']
             },
            {'node_type': get_id('node_types', 'scene'),
             'permissions': ['GET', 'UPDATE', 'DELETE']
             },
            {'node_type': get_id('node_types', 'act'),
             'permissions': ['GET', 'UPDATE', 'DELETE']
             },
            {'node_type': get_id('node_types', 'comment'),
             'permissions': ['GET', 'UPDATE', 'DELETE']
             },
        ]
    }
    post_item('groups', owner_group)

    world_group = {
        'name': 'world',
        'permissions': [
            {'node_type': get_id('node_types', 'shot'),
             'permissions': ['GET']
             },
            {'node_type': get_id('node_types', 'task'),
             'permissions': ['GET']
             },
            {'node_type': get_id('node_types', 'scene'),
             'permissions': ['GET']
             },
            {'node_type': get_id('node_types', 'act'),
             'permissions': ['GET']
             },
            {'node_type': get_id('node_types', 'comment'),
             'permissions': ['GET', 'POST']
             },
        ]
    }
    post_item('groups', world_group)


@manager.command
def populate_db_test():
    """Populate the db with sample data
    """
    populate_node_types()


def populate_node_types(old_ids={}):
    shot_node_type = {
        "name": "shot",
        "description": "Shot Node Type, for shots",
        "dyn_schema": {
            "url": {
                "type": "string",
            },
            "cut_in": {
                "type": "integer"
            },
            "cut_out": {
                "type": "integer"
            },
            "status": {
                "type": "string",
                "allowed": [
                    "on_hold",
                    "todo",
                    "in_progress",
                    "review",
                    "final"
                ],
            },
            "notes": {
                "type": "string",
                "maxlength": 256,
            },
            "shot_group": {
                "type": "string",
                #"data_relation": {
                #    "resource": "nodes",
                #    "field": "_id",
                #},
            },
        },
        "form_schema": {
            "url": {},
            "cut_in": {},
            "cut_out": {},
            "status": {},
            "notes": {},
            "shot_group": {}
        },
        "parent": {
            "node_types": ["scene"]
        }
    }

    task_node_type = {
        "name": "task",
        "description": "Task Node Type, for tasks",
        "dyn_schema": {
            "status": {
                "type": "string",
                "allowed": [
                    "todo",
                    "in_progress",
                    "on_hold",
                    "approved",
                    "cbb",
                    "final",
                    "review"
                ],
                "required": True,
            },
            "filepath": {
                "type": "string",
            },
            "revision": {
                "type": "integer",
            },
            "owners": {
                "type": "dict",
                "schema": {
                    "users": {
                        "type": "list",
                        "schema": {
                            "type": "objectid",
                        }
                    },
                    "groups": {
                        "type": "list",
                        "schema": {
                            "type": "objectid",
                        }
                    }
                }
            },
            "time": {
                "type": "dict",
                "schema": {
                    "start": {
                        "type": "datetime"
                    },
                    "duration": {
                        "type": "integer"
                    },
                    "chunks": {
                        "type": "list",
                        "schema": {
                            "type": "dict",
                            "schema": {
                                "start": {
                                    "type": "datetime",
                                },
                                "duration": {
                                    "type": "integer",
                                }
                            }
                        }
                    },
                }
            },
            "is_conflicting" : {
                "type": "boolean"
            },
            "is_processing" : {
                "type": "boolean"
            },
            "is_open" : {
                "type": "boolean"
            }

        },
        "form_schema": {
            "status": {},
            "filepath": {},
            "revision": {},
            "owners": {
                "schema": {
                    "users":{
                        "items": [('User', 'first_name')],
                    },
                    "groups": {}
                }
            },
            "time": {
                "schema": {
                    "start": {},
                    "duration": {},
                    "chunks": {
                        "visible": False,
                        "schema": {
                            "start": {},
                            "duration": {}
                        }
                    }
                }
            },
            "is_conflicting": {},
            "is_open": {},
            "is_processing": {},
        },
        "parent": {
            "node_types": ["shot"],
        }
    }

    scene_node_type = {
        'name': 'scene',
        'description': 'Scene node type',
        'dyn_schema': {
            'order': {
                'type': 'integer',
            }
        },
        'form_schema': {
            'order': {},
        },
        'parent': {
            "node_types": ["act"]
        }
    }

    act_node_type = {
        'name': 'act',
        'description': 'Act node type',
        'dyn_schema': {
            'order': {
                'type': 'integer',
            }
        },
        'form_schema': {
            'order': {},
        },
        'parent': {}
    }

    comment_node_type = {
        'name': 'comment',
        'description': 'Comment node type',
        'dyn_schema': {
            'text': {
                'type': 'string',
                'maxlength': 256
            },
            'attachments': {
                'type': 'list',
                'schema': {
                    'type': 'objectid',
                    'data_relation': {
                        'resource': 'files',
                        'field': '_id',
                        'embeddable': True
                    }
                }
            }
        },
        'form_schema': {
            'text': {},
            'attachments': {
                'items': [("File", "name")]
            }
        },
        'parent': {
            "node_types": ["shot", "task"]
        }
    }

    from pymongo import MongoClient

    client = MongoClient()
    db = client.eve

    def mix_node_type(old_id, node_type_dict):
        # Take eve parameters
        node_type = db.node_types.find({'_id':old_id})
        node_type = node_type[0]
        for attr in node_type:
            if attr[0]=='_':
                # Mix with node type attributes
                node_type_dict[attr]=node_type[attr]
        return node_type_dict

    def upgrade(node_type, old_ids):
        node_name = node_type['name']
        if node_name in old_ids:
            node_type = mix_node_type(old_ids[node_name], node_type)
            # Remove old node_type
            db.node_types.remove({'_id': old_ids[node_name]})
            # Insert new node_type
            db.node_types.insert(node_type)
        else:
            post_item('node_types', node_type)

    upgrade(shot_node_type, old_ids)
    upgrade(task_node_type, old_ids)
    upgrade(scene_node_type, old_ids)
    upgrade(act_node_type, old_ids)
    upgrade(comment_node_type, old_ids)


if __name__ == '__main__':
    manager.run()
