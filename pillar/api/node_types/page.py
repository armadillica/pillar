from pillar.api.node_types import _attachments_embedded_schema

node_type_page = {
    'name': 'page',
    'description': 'A single page',
    'dyn_schema': {
        # The page content (Markdown format)
        'content': {
            'type': 'string',
            'minlength': 5,
            'maxlength': 90000,
            'required': True
        },
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
