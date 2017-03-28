from pillar.api.node_types import _file_embedded_schema

node_type_hdri = {
    # When adding this node type, make sure to enable CORS from * on the GCS
    # bucket (https://cloud.google.com/storage/docs/cross-origin)
    'name': 'hdri',
    'description': 'HDR Image',
    'parent': ['group_hdri'],
    'dyn_schema': {
        # Default yaw angle in degrees.
        'default_yaw': {
            'type': 'float',
            'default': 0.0
        },
        'status': {
            'type': 'string',
            'allowed': [
                'published',
                'pending',
            ],
        },
        # Used for sorting within the context of a group
        'order': {'type': 'integer'},
        # We point to the file resloutions (and use it to extract any relevant
        # variation useful for our scope).
        'files': {
            'type': 'list',
            'schema': {
                'type': 'dict',
                'schema': {
                    'file': _file_embedded_schema,
                    'resolution': {
                        'type': 'string',
                        'required': True}
                }
            }
        },
        # Tags for search
        'tags': {
            'type': 'list',
            'schema': {
                'type': 'string'
            }
        },
        # Simple string to represent hierarchical categories. Should follow
        # this schema: "Root > Nested Category > One More Nested Category"
        'categories': {
            'type': 'string'
        },
        'license_type': {
            'default': 'cc-by',
            'type': 'string',
            'allowed': [
                'cc-by',
                'cc-0',
                'cc-by-sa',
                'cc-by-nd',
                'cc-by-nc',
                'copyright'
            ]
        },
        'license_notes': {
            'type': 'string'
        },
    },
    'form_schema': {
        'content_type': {'visible': False},
        'tags': {'visible': False},
        'categories': {'visible': False},
    },
}
