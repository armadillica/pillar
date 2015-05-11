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
                "allowed": ["on_hold",
                            "todo",
                            "in_progress",
                            "review_required",
                            "final"],
            },
            "notes": {
                "type": "string",
                "maxlength": 256,
            },
            "order": {
                "type": "integer",
            },
            "shot_group": {
                "type": "string",
                #"data_relation": {
                #    "resource": "nodes",
                #    "field": "_id",
                #},
            }
        },
        "form_schema": {
            "url": {},
            "cut_in": {},
            "cut_out": {},
            "status": {},
            "notes": {},
            "order": {},
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
                    "in-progress",
                    "done",
                    "cbb",
                    "final1",
                    "final2",
                    "review"
                ],
                "required": True,
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
            }
        },
        "form_schema": {
            "status": {},
            "owners": {
                "schema": {
                    "users":{
                        "items": [('User', 'email')],
                    },
                    "groups":{}
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
            }
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
