import os

from authentication import RolesAuth

# Enable reads (GET), inserts (POST) and DELETE for resources/collections
# (if you omit this line, the API will default to ['GET'] and provide
# read-only access to the endpoint).
RESOURCE_METHODS = ['GET', 'POST', 'DELETE']

# Enable reads (GET), edits (PATCH), replacements (PUT) and deletes of
# individual items  (defaults to read-only item access).
ITEM_METHODS = ['GET', 'PATCH', 'PUT', 'DELETE']


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
        'type': 'string',
        'allowed': ["author", "contributor", "copy"],
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
        'minlength': 1,
        'maxlength': 128,
    },
    'thumbnail': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 128,
    },
    'parent': {
        'type': 'objectid',
         'data_relation': {
             'resource': 'nodes',
             'field': '_id',
         },
    },
    'node_type' : {
        'type' : 'string',
        'required': True,
         'data_relation': {
             'resource': 'node_types',
             'field': '_id',
         },
    },
     'properties' : {
         'type' : 'dict',
         'valid_properties' : True,
         'required': True,
     }
}


node_types_schema = {
    'name': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 128,
        'required': True,
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

    # most global settings can be overridden at resource level
    'resource_methods': ['GET', 'POST'],

    'allowed_roles': ['author', 'contributor'],

    'schema': nodes_schema
}


node_types = {

    'resource_methods': ['GET', 'POST'],

    'schema': node_types_schema,
}


users = {
    'item_title': 'user',

    # by default the standard item entry point is defined as
    # '/people/<ObjectId>'. We leave it untouched, and we also enable an
    # additional read-only entry point. This way consumers can also perform
    # GET requests at '/people/<lastname>'.
    'additional_lookup': {
        'url': 'regex("[\w]+")',
        'field': 'lastname'
    },

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
