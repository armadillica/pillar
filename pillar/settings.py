import os

# Enable reads (GET), inserts (POST) and DELETE for resources/collections
# (if you omit this line, the API will default to ['GET'] and provide
# read-only access to the endpoint).
RESOURCE_METHODS = ['GET', 'POST', 'DELETE']

# Enable reads (GET), edits (PATCH), replacements (PUT) and deletes of
# individual items  (defaults to read-only item access).
ITEM_METHODS = ['GET', 'PUT', 'DELETE', 'PATCH']

PAGINATION_LIMIT = 25

# To be implemented on Eve 0.6
# RETURN_MEDIA_AS_URL = True

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
    'username': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 60,
        'required': True,
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
    },
    'groups': {
        'type': 'list',
        'default': [],
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

organizations_schema = {
    'name': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 128,
        'required': True
    },
    'url': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 128,
        'required': True
    },
    'description': {
        'type': 'string',
        'maxlength': 256,
    },
    'website': {
        'type': 'string',
        'maxlength': 256,
    },
    'location': {
        'type': 'string',
        'maxlength': 256,
    },
    'picture': {
        'type': 'objectid',
        'nullable': True,
        'data_relation': {
           'resource': 'files',
           'field': '_id',
           'embeddable': True
        },
    },
    'users': {
        'type': 'list',
        'default': [],
        'schema': {
            'type': 'objectid',
            'data_relation': {
                'resource': 'users',
                'field': '_id',
                'embeddable': True
            }
        }
    },
    'teams': {
        'type': 'list',
        'default': [],
        'schema': {
            'type': 'dict',
            'schema': {
                # Team name
                'name': {
                    'type': 'string',
                    'minlength': 1,
                    'maxlength': 128,
                    'required': True
                },
                # List of user ids for the team
                'users': {
                    'type': 'list',
                    'default': [],
                    'schema': {
                        'type': 'objectid',
                        'data_relation': {
                            'resource': 'users',
                            'field': '_id',
                        }
                    }
                },
                # List of groups assigned to the team (this will automatically
                # update the groups property of each user in the team)
                'groups': {
                    'type': 'list',
                    'default': [],
                    'schema': {
                        'type': 'objectid',
                        'data_relation': {
                            'resource': 'groups',
                            'field': '_id',
                        }
                    }
                }
            }
        }
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
        'maxlength': 5000,
    },
    'picture': {
        'type': 'objectid',
        'nullable': True,
        'data_relation': {
           'resource': 'files',
           'field': '_id',
           'embeddable': True
        },
    },
    'order': {
        'type': 'integer',
        'minlength': 0,
    },
    'revision': {
        'type': 'integer',
    },
    'parent': {
        'type': 'objectid',
         'data_relation': {
            'resource': 'nodes',
            'field': '_id',
            'embeddable': True
         },
    },
    'user': {
        'type': 'objectid',
        'required': True,
        'data_relation': {
            'resource': 'users',
            'field': '_id',
            'embeddable': True
        },
    },
    'node_type': {
        'type': 'objectid',
        'required': True,
        'data_relation': {
            'resource': 'node_types',
            'field': '_id',
            'embeddable': True
        },
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

files_schema = {
    'name': {
        'type': 'string',
        'required': True,
    },
    'description': {
        'type': 'string',
    },
    # If the object has a parent, it is a variation of its parent. When querying
    # for a file we are going to check if the object does NOT have a parent. In
    # this case we will query for all files with the ObjectID as parent and we
    # will aggregate them according of the type (if it's an image we will use
    # some prefix, if it's a video we will combine the contentType and a custom
    # prefix, such as 720p)
    'parent': {
        'type': 'objectid',
         'data_relation': {
            'resource': 'files',
            'field': '_id',
            'embeddable': True
         },
    },
    'content_type': { # MIME type image/png video/mp4
        'type': 'string',
        'required': True,
    },
    # Duration in seconds, only if it's a video
    'duration': {
        'type': 'integer',
    },
    'size': { # xs, s, b, 720p, 2K
        'type': 'string'
    },
    'format': { # human readable format, like mp4, HLS, webm, mov
        'type': 'string'
    },
    'width': { # valid for images and video content_type
        'type': 'integer'
    },
    'height': {
        'type': 'integer'
    },
    'user': {
        'type': 'objectid',
        'required': True,
    },
    'length': { # Size in bytes
        'type': 'integer',
        'required': True,
    },
    'md5': {
        'type': 'string',
        'required': True,
    },
    'filename': {
        'type': 'string',
        'required': True,
    },
    'backend': {
        'type': 'string',
        'required': True,
        'allowed': ["attract-web", "pillar", "cdnsun"]
    },
    'path': {
        'type': 'string',
        #'required': True,
        'unique': True,
    },
    'previews': { # Deprecated (see comments above)
        'type': 'list',
        'schema': {
            'type': 'objectid',
            'data_relation': {
                'resource': 'files',
                'field': '_id',
                'embeddable': True
            }
        }
    },
    # Preview parameters:
    'is_preview': { # Deprecated
        'type': 'boolean'
    }
}

binary_files_schema = {
    'data': {
        'type': 'media',
        'required': True
    }
}

groups_schema = {
    'name': {
        'type': 'string',
        'required': True
    },
    'permissions': {
        'type': 'list',
        'required': True,
        'schema': {
            'type': 'dict',
            'schema': {
                'node_type': {
                    'type': 'objectid',
                    'required': True,
                    'data_relation': {
                        'resource': 'node_types',
                        'field': '_id',
                        'embeddable': True
                    }
                },
                'permissions': {
                    'type': 'list',
                    'required': True,
                    'allowed': ['GET', 'POST', 'UPDATE', 'DELETE']
                }
            }
        }
    }
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

files = {
    'resource_methods': ['GET', 'POST'],
    'schema': files_schema,
}

binary_files = {
    'resource_methods': ['GET', 'POST'],
    'schema': binary_files_schema,
}

groups = {
    'resource_methods': ['GET', 'POST'],
    'schema': groups_schema,
}

organizations = {
    'schema': organizations_schema,
}

DOMAIN = {
    'users': users,
    'nodes': nodes,
    'node_types': node_types,
    'tokens': tokens,
    'files': files,
    'binary_files': binary_files,
    'groups': groups,
    'organizations': organizations
}

try:
    os.environ['TEST_ATTRACT']
    MONGO_DBNAME = 'attract_test'
except:
    pass

if os.environ.get('MONGO_HOST'):
    MONGO_HOST = os.environ.get('MONGO_HOST')
