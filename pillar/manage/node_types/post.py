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
                'deleted',
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
        }
    },
    'form_schema': {
        'content': {},
        'status': {},
        'category': {},
        'url': {}
    },
    'parent': {
        'node_types': ['blog',]
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

