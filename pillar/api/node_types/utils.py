from pillar import markdown


def markdown_fields(field: str, **kwargs) -> dict:
    """
    Creates a field for the markdown, and a field for the cached html.

    Example usage:
    schema = {'myDoc': {
        'type': 'list',
        'schema': {
            'type': 'dict',
            'schema': {
                **markdown_fields('content', required=True),
            }
        },
    }}

    :param field:
    :return:
    """
    cache_field = markdown.cache_field_name(field)
    return {
        field: {
            'type': 'string',
            **kwargs
        },
        cache_field: {
            'type': 'string',
            'readonly': True,
            'default': field,  # Name of the field containing the markdown. Will be input to the coerce function.
            'coerce': 'markdown',
        }
    }