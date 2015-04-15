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
    except ImportError:
       PORT = 5000
       HOST = '0.0.0.0'
       DEBUG = True

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
            "node_types": []
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
                        "items": ['User'],
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
                            "start":{},
                            "duration":{}
                        }
                    }
                }
            }
        },
        "parent": {
            "node_types": ["shot"],
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


    shot_name = shot_node_type['name']
    if shot_name in old_ids:
        shot_node_type = mix_node_type(old_ids[shot_name], shot_node_type)
        # Remove old node_type
        db.node_types.remove({'_id':old_ids[shot_name]})
        # Insert new node_type
        db.node_types.insert(shot_node_type)
    else:
        post_item('node_types', shot_node_type)


    task_name = task_node_type['name']
    if task_name in old_ids:
        task_node_type = mix_node_type(old_ids[task_name], task_node_type)
        # Remove old node_type
        db.node_types.remove({'_id':old_ids[task_name]})
        # Insert new node_type
        db.node_types.insert(task_node_type)
    else:
        post_item('node_types', task_node_type)


if __name__ == '__main__':
    manager.run()
