_file_embedded_schema = {
    'type': 'objectid',
    'data_relation': {
        'resource': 'files',
        'field': '_id',
        'embeddable': True
    }
}

_attachments_embedded_schema = {
    'type': 'dict',
    # TODO: will be renamed to 'keyschema' in Cerberus 1.0
    'propertyschema': {
        'type': 'string',
        'regex': '^[a-zA-Z0-9_ ]+$',
    },
    'valueschema': {
        'type': 'dict',
        'schema': {
            'oid': {
                'type': 'objectid',
                'required': True,
            },
            'collection': {
                'type': 'string',
                'allowed': ['files'],
                'default': 'files',
            },
        },
    },
}
