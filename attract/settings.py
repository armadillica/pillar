import os

# Enable reads (GET), inserts (POST) and DELETE for resources/collections
# (if you omit this line, the API will default to ['GET'] and provide
# read-only access to the endpoint).
RESOURCE_METHODS = ['GET', 'POST', 'DELETE']

# Enable reads (GET), edits (PATCH), replacements (PUT) and deletes of
# individual items  (defaults to read-only item access).
ITEM_METHODS = ['GET', 'PUT', 'DELETE']


users_schema = {
    'firstname': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 10,
    },
    'lastname': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 15,
    },
    'role': {
        'type': 'list',
        'allowed': ["admin"],
        'required': True,
    },
    # An embedded 'strongly-typed' dictionary.
    'location': {
        'type': 'dict',
        'schema': {
            'address': {'type': 'string'},
            'city': {'type': 'string'}
        }
    },
    'born': {
        'type': 'datetime',
    },
}

nodes_schema = {
    'name': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 128,
        'required': True,
    },
    'description': {
        'type': 'string',
        'minlength': 0,
        'maxlength': 128,
    },
    'thumbnail': {
        'type': 'string',
        'minlength': 0,
        'maxlength': 128,
    },
    'order': {
        'type': 'integer',
        'minlength': 0,
    },
    'parent': {
        'type': 'objectid',
        'default': '',
         #'data_relation': {
         #    'resource': 'nodes',
         #    'field': '_id',
         #},
    },
    'node_type': {
        'type': 'objectid',
        'required': True,
        #'data_relation': {
        #     'resource': 'node_types',
        #     'field': '_id',
        #},
    },
     'properties': {
         'type' : 'dict',
         'valid_properties' : True,
         'required': True,
     },
}


node_types_schema = {
    'name': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 128,
        'required': True,
    },
    'description': {
        'type': 'string',
        'maxlength': 256,
    },
    'dyn_schema': {
        'type': 'dict',
        'required': True,
    }
}


tokens_schema = {
    'username': {
        'type': 'string',
        'required': True,
    },
    'token': {
        'type': 'string',
    }
}


nodes = {
    # We choose to override global cache-control directives for this resource.
    'cache_control': 'max-age=10,must-revalidate',
    'cache_expires': 10,

    'schema': nodes_schema
}


node_types = {
    'resource_methods': ['GET', 'POST'],
    'schema': node_types_schema,
}


users = {
    'item_title': 'user',

    # We choose to override global cache-control directives for this resource.
    'cache_control': 'max-age=10,must-revalidate',
    'cache_expires': 10,

    # most global settings can be overridden at resource level
    'resource_methods': ['GET', 'POST'],

    'public_methods': ['GET', 'POST'],
    # 'public_item_methods': ['GET'],

    'schema': users_schema
}

tokens = {
    'resource_methods': ['POST'],

    # Allow 'token' to be returned with POST responses
    'extra_response_fields': ['token'],

    'schema' : tokens_schema
}

DOMAIN = {
    'users': users,
    'nodes' : nodes,
    'node_types': node_types,
    'tokens': tokens,
}

try:
    os.environ['TEST_ATTRACT']
    MONGO_DBNAME = 'attract_test'
except:
    pass
