node_type_group_texture = {
    'name': 'group_texture',
    'description': 'Group for texture node type',
    'parent': {
        'node_types': ['group_texture', 'project']
    },
    'dyn_schema': {
        # Used for sorting within the context of a group
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
                'deleted'
            ],
        }
    },
    'form_schema': {
        'url': {},
        'status': {},
        'order': {}
    },
    'permissions': {
    }
}
