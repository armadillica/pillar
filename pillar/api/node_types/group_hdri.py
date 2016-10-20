node_type_group_hdri = {
    'name': 'group_hdri',
    'description': 'Group for HDRi node type',
    'parent': ['group_hdri', 'project'],
    'dyn_schema': {
        # Used for sorting within the context of a group
        'order': {
            'type': 'integer'
        },
        'status': {
            'type': 'string',
            'allowed': [
                'published',
                'pending',
            ],
        }
    },
    'form_schema': {},
}
