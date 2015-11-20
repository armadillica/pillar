from manage.node_types import _file_embedded_schema

node_type_asset = {
    'name': 'asset',
    'description': 'Basic Asset Type',
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
                'processing',
                'deleted'
            ],
        },
        # Used for sorting within the context of a group
        'order': {
            'type': 'integer'
        },
        # We expose the type of asset we point to. Usually image, video,
        # zipfile, ect.
        'content_type': {
            'type': 'string'
        },
        # We point to the original file (and use it to extract any relevant
        # variation useful for our scope).
        'file': _file_embedded_schema,
        'attachments': {
            'type': 'list',
            'schema': {
            'type': 'dict',
                'schema': {
                    'field': {'type': 'string'},
                    'files' : {
                        'type': 'list',
                        'schema': {
                            'type': 'dict',
                            'schema': {
                                'file': _file_embedded_schema,
                                'slug': {'type': 'string', 'minlength': 1},
                                'size': {'type': 'string'}
                            }
                        }
                    }
                }
            }
        }
    },
    'form_schema': {
        'status': {},
        'content_type': {'visible': False},
        'file': {'visible': False},
        'attachments': {'visible': False},
        'order': {}
    },
    'permissions': {
        # 'groups': [{
        #     'group': app.config['ADMIN_USER_GROUP'],
        #     'methods': ['GET', 'PUT', 'POST']
        # }],
        # 'users': [],
    }
}
