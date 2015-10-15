import os

# Enable reads (GET), inserts (POST) and DELETE for resources/collections
# (if you omit this line, the API will default to ['GET'] and provide
# read-only access to the endpoint).
RESOURCE_METHODS = ['GET', 'POST', 'DELETE']

# Enable reads (GET), edits (PATCH), replacements (PUT) and deletes of
# individual items  (defaults to read-only item access).
ITEM_METHODS = ['GET', 'PUT', 'DELETE', 'PATCH']

PAGINATION_LIMIT = 25


users_schema = {
    'full_name': {
        'type': 'string',
        'minlength': 1,
        'maxlength': 128,
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
    'roles': {
        'type': 'list',
        'allowed': ["admin"],
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
    },
    'auth': {
        # Storage of authentication credentials (one will be able to auth with
        # multiple providers on the same account)
        'type': 'list',
        'required': True,
        'schema': {
            'type': 'dict',
            'schema': {
                'provider': {
                    'type': 'string',
                    'allowed': ["blender-id",],
                },
                'user_id' : {
                    'type': 'string'
                },
                'token': {
                    'type': 'string'
                }
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
    'email': {
        'type': 'string'
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

permissions_embedded_schema = {
    'groups': {
        'type': 'list',
        'schema': {
            'type': 'dict',
            'schema': {
                'group': {
                    'type': 'objectid',
                    'required': True,
                    'data_relation': {
                        'resource': 'groups',
                        'field': '_id',
                        'embeddable': True
                    }
                },
                'methods': {
                    'type': 'list',
                    'required': True,
                    'allowed': ['GET', 'PUT', 'POST', 'DELETE']
                }
            }
        },
    },
    'users': {
        'type': 'list',
        'schema': {
            'type': 'dict',
            'schema': {
                'user' : {
                    'type': 'objectid',
                    'required': True,
                },
                'methods': {
                    'type': 'list',
                    'required': True,
                    'allowed': ['GET', 'PUT', 'POST', 'DELETE']
                }
            }
        }
    },
    'world': {
        'type': 'list',
        #'required': True,
        'allowed': ['GET',]
    },
    'is_free': {
        'type': 'boolean',
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
    'permissions': {
        'type': 'dict',
        'schema': permissions_embedded_schema
    }
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
    },
    'permissions': {
        'type': 'dict',
        'required': True,
        'schema': permissions_embedded_schema
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
    'schema': nodes_schema,
    'public_methods': ['GET'],
    'public_item_methods': ['GET']
}

node_types = {
    'resource_methods': ['GET', 'POST'],
    'public_methods': ['GET'],
    'public_item_methods': ['GET'],
    'schema': node_types_schema,
}

users = {
    'item_title': 'user',

    # We choose to override global cache-control directives for this resource.
    'cache_control': 'max-age=10,must-revalidate',
    'cache_expires': 10,

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
    'public_methods': ['GET'],
    'public_item_methods': ['GET'],
    'schema': files_schema
}

groups = {
    'resource_methods': ['GET', 'POST'],
    'public_methods': ['GET'],
    'public_item_methods': ['GET'],
    'schema': groups_schema,
}

organizations = {
    'schema': organizations_schema,
    'public_item_methods': ['GET'],
    'public_methods': ['GET']
}

DOMAIN = {
    'users': users,
    'nodes': nodes,
    'node_types': node_types,
    'tokens': tokens,
    'files': files,
    'groups': groups,
    'organizations': organizations
}


MONGO_HOST = os.environ.get('MONGO_HOST', 'localhost')
MONGO_PORT = os.environ.get('MONGO_PORT', 27017)
