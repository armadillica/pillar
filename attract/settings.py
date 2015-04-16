import os

# Enable reads (GET), inserts (POST) and DELETE for resources/collections
# (if you omit this line, the API will default to ['GET'] and provide
# read-only access to the endpoint).
RESOURCE_METHODS = ['GET', 'POST', 'DELETE']

# Enable reads (GET), edits (PATCH), replacements (PUT) and deletes of
# individual items  (defaults to read-only item access).
ITEM_METHODS = ['GET', 'PUT', 'DELETE', 'PATCH']
# EXTENDED_MEDIA_INFO = ['_id', 'content_type', 'name', 'length']
RETURN_MEDIA_AS_URL = True
RETURN_MEDIA_AS_BASE64_STRING = False

PAGINATION_LIMIT = 100

users_schema = {
    'first_name': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 60,
    },
    'last_name': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 60,
    },
    'email': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 60,
    },
    'role': {
        'type': 'list',
        'allowed': ["admin"],
        'required': True,
    }
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
    'picture': {
        'type': 'objectid'
    },
    'order': {
        'type': 'integer',
        'minlength': 0,
    },
    'parent': {
        'type': 'objectid',
         #'default': '',
         #'data_relation': {
         #    'resource': 'nodes',
         #    'field': '_id',
         #},
    },
    'user': {
        'type': 'objectid',
        'required': True,
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
    },
    'form_schema': {
        'type': 'dict',
        'required': True,
    },
    'parent': {
        'type': 'dict',
        'required': True,
    }
}

tokens_schema = {
    'user': {
        'type': 'objectid',
        'required': True,
    },
    'token': {
        'type': 'string',
        'required': True,
    },
    'expire_time': {
        'type': 'datetime',
        'required': True,
    },
}

nodes = {
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
    'resource_methods': ['GET', 'POST'],

    # Allow 'token' to be returned with POST responses
    #'extra_response_fields': ['token'],

    'schema' : tokens_schema
}

DOMAIN = {
    'users': users,
    'nodes': nodes,
    'node_types': node_types,
    'tokens': tokens,
}

try:
    os.environ['TEST_ATTRACT']
    MONGO_DBNAME = 'attract_test'
except:
    pass
