node_type_group = {
    'name': 'group',
    'description': 'Generic group node type',
    'parent': {
        'node_types': ['group', 'project']
    },
    'dyn_schema': {
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
        },
        'notes': {
            'type': 'string',
            'maxlength': 256,
        },
    },
    'form_schema': {
        'url': {},
        'status': {},
        'notes': {},
    },
    'permissions': {
        # 'groups': [{
        #     'group': app.config['ADMIN_USER_GROUP'],
        #     'methods': ['GET', 'PUT', 'POST']
        # }],
        # 'users': [],
        # 'world': ['GET']
    }
}
