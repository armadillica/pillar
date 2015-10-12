import os
from eve.methods.put import put_internal
from application import app
from application import db
from application import post_item
from flask.ext.script import Manager

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
    """Wipes node_types collection
    and populates it again
    """
    from pymongo import MongoClient

    client = MongoClient(MONGO_HOST, 27017)
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
def populate_db():
    """Populate the db with sample data
    """
    populate_node_types()


def populate_node_types(old_ids={}):
    shot_node_type = {
        'name': 'shot',
        'description': 'Shot Node Type, for shots',
        'dyn_schema': {
            'url': {
                'type': 'string',
            },
            'cut_in': {
                'type': 'integer'
            },
            'cut_out': {
                'type': 'integer'
            },
            'status': {
                'type': 'string',
                'allowed': [
                    'on_hold',
                    'todo',
                    'in_progress',
                    'review',
                    'final'
                ],
            },
            'notes': {
                'type': 'string',
                'maxlength': 256,
            },
            'shot_group': {
                'type': 'string',
                #'data_relation': {
                #    'resource': 'nodes',
                #    'field': '_id',
                #},
            },
        },
        'form_schema': {
            'url': {},
            'cut_in': {},
            'cut_out': {},
            'status': {},
            'notes': {},
            'shot_group': {}
        },
        'parent': {
            'node_types': ['scene']
        }
    }

    task_node_type = {
        'name': 'task',
        'description': 'Task Node Type, for tasks',
        'dyn_schema': {
            'status': {
                'type': 'string',
                'allowed': [
                    'todo',
                    'in_progress',
                    'on_hold',
                    'approved',
                    'cbb',
                    'final',
                    'review'
                ],
                'required': True,
            },
            'filepath': {
                'type': 'string',
            },
            'revision': {
                'type': 'integer',
            },
            'owners': {
                'type': 'dict',
                'schema': {
                    'users': {
                        'type': 'list',
                        'schema': {
                            'type': 'objectid',
                        }
                    },
                    'groups': {
                        'type': 'list',
                        'schema': {
                            'type': 'objectid',
                        }
                    }
                }
            },
            'time': {
                'type': 'dict',
                'schema': {
                    'start': {
                        'type': 'datetime'
                    },
                    'duration': {
                        'type': 'integer'
                    },
                    'chunks': {
                        'type': 'list',
                        'schema': {
                            'type': 'dict',
                            'schema': {
                                'start': {
                                    'type': 'datetime',
                                },
                                'duration': {
                                    'type': 'integer',
                                }
                            }
                        }
                    },
                }
            },
            'is_conflicting' : {
                'type': 'boolean'
            },
            'is_processing' : {
                'type': 'boolean'
            },
            'is_open' : {
                'type': 'boolean'
            }

        },
        'form_schema': {
            'status': {},
            'filepath': {},
            'revision': {},
            'owners': {
                'schema': {
                    'users':{
                        'items': [('User', 'first_name')],
                    },
                    'groups': {}
                }
            },
            'time': {
                'schema': {
                    'start': {},
                    'duration': {},
                    'chunks': {
                        'visible': False,
                        'schema': {
                            'start': {},
                            'duration': {}
                        }
                    }
                }
            },
            'is_conflicting': {},
            'is_open': {},
            'is_processing': {},
        },
        'parent': {
            'node_types': ['shot'],
        }
    }

    scene_node_type = {
        'name': 'scene',
        'description': 'Scene node type',
        'parent': {
            "node_types": ["act"]
        }
    }

    act_node_type = {
        'name': 'act',
        'description': 'Act node type',
        'parent': {}
    }


    node_type_project = {
        'name': 'project',
        'parent': {},
        'description': 'The official project type',
        'dyn_schema': {
            'category': {
                'type': 'string',
                'allowed': [
                    'training',
                    'film',
                    'assets',
                    'software',
                    'game'
                ],
                'required': True,
            },
            'is_private': {
                'type': 'boolean'
            },
            'url': {
                'type': 'string'
            },
            'organization': {
                'type': 'objectid',
                'nullable': True,
                'data_relation': {
                   'resource': 'organizations',
                   'field': '_id',
                   'embeddable': True
                },
            },
            'owners': {
                'type': 'dict',
                'schema': {
                    'users': {
                        'type': 'list',
                        'schema': {
                            'type': 'objectid',
                        }
                    },
                    'groups': {
                        'type': 'list',
                        'schema': {
                            'type': 'objectid',
                            'data_relation': {
                                'resource': 'groups',
                                'field': '_id',
                                'embeddable': True
                            }
                        }
                    }
                }
            },
            # Logo
            'picture_square': {
                'type': 'objectid',
                'nullable': True,
                'data_relation': {
                   'resource': 'files',
                   'field': '_id',
                   'embeddable': True
                },
            },
            # Header
            'picture_header': {
                'type': 'objectid',
                'nullable': True,
                'data_relation': {
                   'resource': 'files',
                   'field': '_id',
                   'embeddable': True
                },
            },
            # Short summary for the project
            'summary': {
                'type': 'string',
                'maxlength': 128
            }
        },
        'form_schema': {
            'is_private': {},
            # TODO add group parsing
            'category': {},
            'url': {},
            'organization': {},
            'picture_square': {},
            'picture_header': {},
            'summary': {},
            'owners': {
                'schema': {
                    'users':{
                        'items': [('User', 'first_name')],
                    },
                    'groups': {
                        'items': [('Group', 'name')],
                    },
                }
            },
        },
        'permissions': {
            'groups': [{
                'group': '5596e975ea893b269af85c0e',
                'methods': ['GET', 'PUT', 'POST']
            }],
            'users': [],
            'world': ['GET']
        }
    }

    node_type_group = {
        'name': 'group',
        'description': 'Generic group node type',
        'parent': {},
        'dyn_schema': {
            'url': {
                'type': 'string',
            },
            'status': {
                'type': 'string',
                'allowed': [
                    'published',
                    'pending'
                ],
            },
            'notes': {
                'type': 'string',
                'maxlength': 256,
            },
        },
        'form_schema': {
            'url': {},
            'status': {},
            'notes': {},
        },
        'permissions': {
            'groups': [{
                'group': '5596e975ea893b269af85c0e',
                'methods': ['GET', 'PUT', 'POST']
            }],
            'users': [],
            'world': ['GET']
        }
    }

    node_type_asset = {
        'name': 'asset',
        'description': 'Assets for Elephants Dream',
        # This data type does not have parent limitations (can be child
        # of any node). An empty parent declaration is required.
        'parent': {
            "node_types": ["group",]
        },
        'dyn_schema': {
            'status': {
                'type': 'string',
                'allowed': [
                    'published',
                    'pending',
                    'processing'
                ],
            },
            # We expose the type of asset we point to. Usually image, video,
            # zipfile, ect.
            'content_type':{
                'type': 'string'
            },
            # We point to the original file (and use it to extract any relevant
            # variation useful for our scope).
            'file': {
                'type': 'objectid',
                'data_relation': {
                    'resource': 'files',
                    'field': '_id',
                    'embeddable': True
                },
            }
        },
        'form_schema': {
            'status': {},
            'content_type': {'visible': False},
            'file': {'visible': False},
        },
        'permissions': {
            'groups': [{
                'group': '5596e975ea893b269af85c0e',
                'methods': ['GET', 'PUT', 'POST']
            }],
            'users': [],
            'world': ['GET']
        }
    }

    node_type_storage = {
        'name': 'storage',
        'description': 'Entrypoint to a remote or local storage solution',
        'dyn_schema': {
            # The project ID, use for lookups in the storage backend. For example
            # when using Google Cloud Storage, the project id will be the name
            # of the bucket.
            'project': {
                'type': 'objectid',
                'data_relation': {
                    'resource': 'nodes',
                    'field': '_id'
                },
            },
            # The entry point in a subdirectory of the main storage for the project
            'subdir': {
                'type': 'string',
            },
            # Which backend is used to store the files (gcs, pillar, bam, cdnsun)
            'backend': {
                'type': 'string',
            },
        },
        'form_schema': {
            'subdir': {},
            'project': {},
            'backend': {}
        },
        'parent': {
            "node_types": ["group", "project"]
        },
        'permissions': {
            'groups': [{
                'group': '5596e975ea893b269af85c0e',
                'methods': ['GET', 'PUT', 'POST']
            }],
            'users': [],
            'world': ['GET']
        }
    }

    node_type_comment = {
        'name': 'comment',
        'description': 'Comments for asset asset nodes, pages, etc.',
        'dyn_schema': {
            # The actual comment content (initially Markdown format)
            'content': {
                'type': 'string',
                'minlength': 5,
            },
            'status': {
                'type': 'string',
                'allowed': [
                    'published',
                    'deleted',
                    'flagged',
                    'edited'
                ],
            },
            # Total count of positive ratings (updated at every rating action)
            'rating_positive': {
                'type': 'integer',
            },
            # Total count of negative ratings (updated at every rating action)
            'rating_negative': {
                'type': 'integer',
            },
            # Collection of ratings, keyed by user
            'ratings': {
                'type': 'list',
                'schema': {
                    'type': 'dict',
                    'schema': {
                        'user': {
                            'type': 'objectid'
                        },
                        'is_positive': {
                            'type': 'boolean'
                        },
                        # Weight of the rating based on user rep and the context.
                        # Currently we have the following weights:
                        # - 1 auto null
                        # - 2 manual null
                        # - 3 auto valid
                        # - 4 manual valid
                        'weight': {
                            'type': 'integer'
                        }
                    }
                }
            },
            'confidence': {
                'type': 'float'
            }

        },
        'form_schema': {
            'content': {},
            'status': {},
            'rating_positive': {},
            'rating_negative': {},
            'ratings': {},
            'confidence': {}
        },
        'parent': {
            'node_types': ['asset',]
        },
        'permissions': {
            'groups': [{
                'group': '5596e975ea893b269af85c0e',
                'methods': ['GET', 'PUT', 'POST']
            }],
            'users': [],
            'world': ['GET']
        }
    }

    from pymongo import MongoClient

    client = MongoClient(MONGO_HOST, 27017)
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
        print("Node {0}".format(node_type['name']))
        node_name = node_type['name']
        if node_name in old_ids:
            node_type = mix_node_type(old_ids[node_name], node_type)
            node_id = node_type['_id']

            # Removed internal fields that would cause validation error
            internal_fields = ['_id', '_etag', '_updated', '_created']
            for field in internal_fields:
                node_type.pop(field, None)

            p = put_internal('node_types', node_type, **{'_id': node_id})
            print p

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


@manager.command
def add_file_video():
    from datetime import datetime
    RFC1123_DATE_FORMAT = '%a, %d %b %Y %H:%M:%S GMT'
    video = {
        'name': 'Video test',
        'description': 'Video test description',
        # 'parent': 'objectid',
        'content_type': 'video/mp4',
        # Duration in seconds, only if it's a video
        'duration': 50,
        'size': '720p',
        'format': 'mp4',
        'width': 1280,
        'height': 720,
        'user': '552b066b41acdf5dec4436f2',
        'length': 15000,
        'md5': 'md5',
        'filename': 'The file name',
        'backend': 'pillar',
        'path': '0000.mp4',
    }
    r = post_item('files', video)
    return r

@manager.command
def add_node_asset(file_id):
    """Creates a node of type asset, starting from an existing file id.
    :param file_id: the file id to use
    :param picture_id: the picture id to use
    :param group_id: the parent folder
    """
    picture_id = None
    parent_id = None

    from bson.objectid import ObjectId
    from pymongo import MongoClient
    client = MongoClient(MONGO_HOST, 27017)
    db = client.eve
    file_object = db.files.find_one({"_id": ObjectId(file_id)})
    node_type = db.node_types.find_one({"name": "asset"})

    print file_object['content_type'].split('/')[0]

    node = {
        'name': file_object['name'],
        'description': file_object['description'],
        #'picture': picture_id,
        #'parent': parent_id,
        'user': file_object['user'],
        'node_type': node_type['_id'],
        'properties': {
            'status': 'published',
            'content_type': file_object['content_type'].split('/')[0],
            'file': file_id
            }
        }
    r = post_item('nodes', node)

    return r

@manager.command
def import_data(path):
    import json
    import pprint
    from bson import json_util
    if not os.path.isfile(path):
        return "File does not exist"
    with open(path, 'r') as infile:
        d = json.load(infile)

    def commit_object(collection, f, parent=None):
        variation_id = f.get('variation_id')
        if variation_id:
            del f['variation_id']

        asset_id = f.get('asset_id')
        if asset_id:
            del f['asset_id']

        node_id = f.get('node_id')
        if node_id:
            del f['node_id']

        if parent:
            f['parent'] = parent
        else:
            if f.get('parent'):
                del f['parent']

        #r = [{'_status': 'OK', '_id': 'DRY-ID'}]
        r = post_item(collection, f)
        if r[0]['_status'] == 'ERR':
            print r[0]['_issues']
            print "Tried to commit the following object"
            pprint.pprint(f)

        # Assign the Mongo ObjectID
        f['_id'] = str(r[0]['_id'])
        # Restore variation_id
        if variation_id:
            f['variation_id'] = variation_id
        if asset_id:
            f['asset_id'] = asset_id
        if node_id:
            f['node_id'] = node_id
        try:
            print "{0} {1}".format(f['_id'], f['name'])
        except UnicodeEncodeError:
            print "{0}".format(f['_id'])
        return f

    # Build list of parent files
    parent_files = [f for f in d['files'] if 'parent_asset_id' in f]
    children_files = [f for f in d['files'] if 'parent_asset_id' not in f]

    for p in parent_files:
        # Store temp property
        parent_asset_id = p['parent_asset_id']
        # Remove from dict to prevent invalid submission
        del p['parent_asset_id']
        # Commit to database
        p = commit_object('files', p)
        # Restore temp property
        p['parent_asset_id'] = parent_asset_id
        # Find children of the current file
        children = [c for c in children_files if c['parent'] == p['variation_id']]
        for c in children:
            # Commit to database with parent id
            c = commit_object('files', c, p['_id'])


    # Merge the dicts and replace the original one
    d['files'] = parent_files + children_files

    # Files for picture previews of folders (groups)
    for f in d['files_group']:
        item_id = f['item_id']
        del f['item_id']
        f = commit_object('files', f)
        f['item_id'] = item_id

    # Files for picture previews of assets
    for f in d['files_asset']:
        item_id = f['item_id']
        del f['item_id']
        f = commit_object('files',f)
        f['item_id'] = item_id


    nodes_asset = [n for n in d['nodes'] if 'asset_id' in n]
    nodes_group = [n for n in d['nodes'] if 'node_id' in n]

    def get_parent(node_id):
        #print "Searching for {0}".format(node_id)
        try:
            parent = [p for p in nodes_group if p['node_id'] == node_id][0]
        except IndexError:
            return None
        return parent

    def traverse_nodes(parent_id):
        parents_list = []
        while True:
            parent = get_parent(parent_id)
            #print parent
            if not parent:
                break
            else:
                parents_list.append(parent['node_id'])
                if parent.get('parent'):
                    parent_id = parent['parent']
                else:
                    break
        parents_list.reverse()
        return parents_list

    for n in nodes_asset:
        node_type_asset = db.node_types.find_one({"name": "asset"})
        if n.get('picture'):
            filename = os.path.splitext(n['picture'])[0]
            pictures = [p for p in d['files_asset'] if p['name'] == filename]
            if pictures:
                n['picture'] = pictures[0]['_id']
                print "Adding picture link {0}".format(n['picture'])
        n['node_type'] = node_type_asset['_id']
        # An asset node must have a parent
        # parent = [p for p in nodes_group if p['node_id'] == n['parent']][0]
        parents_list = traverse_nodes(n['parent'])

        tree_index = 0
        for node_id in parents_list:
            node = [p for p in nodes_group if p['node_id'] == node_id][0]

            if node.get('_id') is None:
                node_type_group = db.node_types.find_one({"name": "group"})
                node['node_type'] = node_type_group['_id']
                # Assign picture to the node group
                if node.get('picture'):
                    filename = os.path.splitext(node['picture'])[0]
                    picture = [p for p in d['files_group'] if p['name'] == filename][0]
                    node['picture'] = picture['_id']
                    print "Adding picture link to node {0}".format(node['picture'])
                if tree_index == 0:
                    # We are at the root of the tree (so we link to the project)
                    node_type_project = db.node_types.find_one({"name": "project"})
                    node['node_type'] = node_type_project['_id']
                    parent = None
                    if node['properties'].get('picture_square'):
                        filename = os.path.splitext(node['properties']['picture_square'])[0]
                        picture = [p for p in d['files_group'] if p['name'] == filename][0]
                        node['properties']['picture_square'] = picture['_id']
                        print "Adding picture_square link to node"
                    if node['properties'].get('picture_header'):
                        filename = os.path.splitext(node['properties']['picture_header'])[0]
                        picture = [p for p in d['files_group'] if p['name'] == filename][0]
                        node['properties']['picture_header'] = picture['_id']
                        print "Adding picture_header link to node"
                else:
                    # Get the parent node id
                    parents_list_node_id = parents_list[tree_index - 1]
                    parent_node = [p for p in nodes_group if p['node_id'] == parents_list_node_id][0]
                    parent = parent_node['_id']
                print "About to commit Node"
                commit_object('nodes', node, parent)
            tree_index += 1
        # Commit the asset
        print "About to commit Asset {0}".format(n['asset_id'])
        parent_node = [p for p in nodes_group if p['node_id'] == parents_list[-1]][0]
        try:
            asset_file = [a for a in d['files'] if a['md5'] == n['properties']['file']][0]
            n['properties']['file'] = str(asset_file['_id'])
            commit_object('nodes', n, parent_node['_id'])
        except IndexError:
            pass

    return


    # New path with _
    path = '_' + path
    with open(path, 'w') as outfile:
        json.dump(d, outfile, default=json_util.default)
    return

@manager.command
def make_thumbnails():
    from application.modules.file_storage import build_thumbnails
    files = db.files.find()
    for f in files:
        if f['content_type'].split('/')[0] == 'image':

            if '-' in f['path']:
                pass
                #print "Skipping {0}".format(f['path'])
            else:
                print "Building {0}".format(f['path'])
                t = build_thumbnails(file_path=f['path'])
                print t

@manager.command
def add_node_permissions():
    import codecs
    import sys
    UTF8Writer = codecs.getwriter('utf8')
    sys.stdout = UTF8Writer(sys.stdout)
    nodes_collection = app.data.driver.db['nodes']
    node_types_collection = app.data.driver.db['node_types']
    nodes = nodes_collection.find()
    for node in nodes:
        print u"{0}".format(node['name'])
        if 'permissions' not in node:
            node_type = node_types_collection.find_one(node['node_type'])
            # nodes_collection.update({'_id': node['_id']},
            #                 {"$set": {'permissions': node_type['permissions']}})
            print node['_id']
        break

if __name__ == '__main__':
    manager.run()
