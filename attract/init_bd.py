from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from bson import ObjectId
from datetime import datetime

client = MongoClient()
db = client.eve

default_user = {
    "_id": ObjectId("550171c8135d3248e477f288"),
    "_updated": datetime.now(),
    "firstname": "admin",
    "lastname": "admin",
    "role": "admin",
    "email": "admin@admin.com",
    "_created": datetime.now(),
    "_etag": "302236e27f51d2e26041ae9de49505d77332b260"
    }

default_token = {
    "_id": ObjectId("5502f289135d3274cb658ba7"),
    "username": "admin",
    "token": "ANLGNSIEZJ",
    "_etag": "1e96ed46b133b7ede5ce6ef0d6d4fc53edd9f2ba"
    }

shot_node_type = {
    "_id": ObjectId("55016a52135d32466fc800be"),
    "_updated": datetime.now(),
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
    "_created": datetime.now(),
    "_etag": "0ea3c4f684a0cda85525184d5606c4f4ce6ac5f5"
    }

shot = {
    "_id": ObjectId("55016a52135d32466fc800be"),
    "_update": datetime.now(),
    "_created": datetime.now(),
    "_etag": "0ea3c4f684a0cda85525184d5606c4f4ce6ac5f5",
    "name": "01",
    "description": "A sheep tries to hang itself, but fails",
    "thumbnail": "/tmp/attrackt-thumbnail.png",
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

try:
    db.users.insert(default_user)
except DuplicateKeyError:
    print ("default_user already exist")

try:
    db.node_types.insert(shot_node_type)
except DuplicateKeyError:
    print ("shot_node_type already exist")

try:
    db.tokens.insert(default_token)
except DuplicateKeyError:
    print ("default_token already exist")

try:
    db.nodes.insert(shot)
except DuplicateKeyError:
    print ("shot already exist")
