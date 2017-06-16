from pillar.api.node_types import _attachments_embedded_schema

node_type_page = {
    'name': 'page',
    'description': 'A single page',
    'dyn_schema': {
        'status': {
            'type': 'string',
            'allowed': [
                'published',
                'pending'
            ],
            'default': 'pending'
        },
        'url': {
            'type': 'string'
        },
        'attachments': _attachments_embedded_schema,
    },
    'form_schema': {
        'attachments': {'visible': False},
    },
    'parent': ['project', ],
}
