from pillar.api.node_types import attachments_embedded_schema

node_type_post = {
    'name': 'post',
    'description': 'A blog post, for any project',
    'dyn_schema': {
        # The blogpost content (Markdown format)
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
        # Global categories, will be enforced to be 1 word
        'category': {
            'type': 'string',
        },
        'url': {
            'type': 'string'
        },
        'attachments': attachments_embedded_schema,
    },
    'form_schema': {
        'attachments': {'visible': False},
    },
    'parent': ['blog', ],
}
