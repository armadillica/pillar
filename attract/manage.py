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
def populate_db_test():
    """Populate the db with sample data
    """

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
                    },
                    "groups": {
                        "type": "list",
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
                    }
                }
            }
        },
    }

    shot = {
        "name": "01",
        "description": "A sheep tries to hang itself, but fails",
        "picture": "",
        "order": 0,
        "parent": None,
        "node_type": "55016a52135d32466fc800be",
        "properties": {
            "url": "shot01",
            "cut_in": 100,
            "cut_out": 900,
            "status": "todo",
            "notes": "I think the sheep should scream a bit more",
            "order": 1,
            "shot_group": "",
        }
    }

    post_item('node_types', shot_node_type)
    post_item('node_types', task_node_type)


if __name__ == '__main__':
    manager.run()
