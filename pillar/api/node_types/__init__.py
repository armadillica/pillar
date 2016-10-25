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

# Import after defining the common embedded schemas, to prevent dependency cycles.
from pillar.api.node_types.asset import node_type_asset
from pillar.api.node_types.blog import node_type_blog
from pillar.api.node_types.comment import node_type_comment
from pillar.api.node_types.group import node_type_group
from pillar.api.node_types.group_hdri import node_type_group_hdri
from pillar.api.node_types.group_texture import node_type_group_texture
from pillar.api.node_types.hdri import node_type_hdri
from pillar.api.node_types.page import node_type_page
from pillar.api.node_types.post import node_type_post
from pillar.api.node_types.storage import node_type_storage
from pillar.api.node_types.text import node_type_text
from pillar.api.node_types.texture import node_type_texture

PILLAR_NODE_TYPES = (node_type_asset, node_type_blog, node_type_comment, node_type_group,
                     node_type_group_hdri, node_type_group_texture, node_type_hdri, node_type_page,
                     node_type_post, node_type_storage, node_type_text, node_type_texture)
PILLAR_NAMED_NODE_TYPES = {nt['name']: nt for nt in PILLAR_NODE_TYPES}
