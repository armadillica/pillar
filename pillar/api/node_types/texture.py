from pillar.api.node_types import _file_embedded_schema

node_type_texture = {
    'name': 'texture',
    'description': 'Image Texture',
    # This data type does not have parent limitations (can be child
    # of any node). An empty parent declaration is required.
    'parent': ['group', ],
    'dyn_schema': {
        'status': {
            'type': 'string',
            'allowed': [
                'published',
                'pending',
            ],
        },
        # Used for sorting within the context of a group
        'order': {'type': 'integer'},
        # We point to the file variations (and use it to extract any relevant
        # variation useful for our scope).
        'files': {
            'type': 'list',
            'schema': {
                'type': 'dict',
                'schema': {
                    'file': _file_embedded_schema,
                    'map_type': {
                        'type': 'string',
                        'allowed': [
                            "alpha",
                            "ambient occlusion",
                            "bump",
                            "color",
                            "displacement",
                            "emission",
                            "glossiness",
                            "id",
                            "mask",
                            "normal",
                            "roughness",
                            "specular",
                            "translucency",
                    ]}
                }
            }
        },
        # Properties of the texture files
        'is_tileable': {'type': 'boolean'},
        'is_landscape': {'type': 'boolean'},
        # Resolution in 'WIDTHxHEIGHT' format (e.g. 512x512)
        'resolution': {'type': 'string'},
        'aspect_ratio': {'type': 'float'},
        # Tags for search
        'tags': {
            'type': 'list',
            'schema': {
                'type': 'string'
            }
        },
        # Simple string to represent hierarchical categories. Should follow
        # this schema: "Root > Nested Category > One More Nested Category"
        'categories': {
            'type': 'string'
        }
    },
    'form_schema': {
        'content_type': {'visible': False},
        'tags': {'visible': False},
        'categories': {'visible': False},
    },
}
