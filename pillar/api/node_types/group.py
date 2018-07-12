node_type_group = {
    'name': 'group',
    'description': 'Folder node type',
    'parent': ['group', 'project'],
    'dyn_schema': {

        'order': {
            'type': 'integer'
        },
        'url': {
            'type': 'string',
        },
        'status': {
            'type': 'string',
            'allowed': [
                'published',
                'pending',
            ],
        },
        'notes': {
            'type': 'string',
            'maxlength': 256,
        }

    },
    'form_schema': {
        'url': {'visible': False},
        'notes': {'visible': False},
        'order': {'visible': False}
    },
}
