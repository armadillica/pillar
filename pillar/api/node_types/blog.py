node_type_blog = {
    'name': 'blog',
    'description': 'Container for node_type post.',
    'dyn_schema': {
        'categories': {
            'type': 'list',
            'schema': {
                'type': 'string'
            }
        }
    },
    'form_schema': {
        'categories': {},
        'template': {},
    },
    'parent': ['project', ],
}
