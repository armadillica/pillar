"""Generic node patching support.

Depends on node_type-specific patch handlers in submodules.
"""

import logging

from flask import Blueprint, request
import werkzeug.exceptions as wz_exceptions

from application.utils import str2id
from application.utils import authorization, mongo, authentication

from . import custom

log = logging.getLogger(__name__)
blueprint = Blueprint('nodes.patch', __name__)


@blueprint.route('/<node_id>', methods=['PATCH'])
@authorization.require_login()
def patch_node(node_id):
    # Parse the request
    node_id = str2id(node_id)
    patch = request.get_json()

    # Find the node type.
    node = mongo.find_one_or_404('nodes', node_id,
                                 projection={'node_type': 1})
    try:
        node_type = node['node_type']
    except KeyError:
        msg = 'Node %s has no node_type property' % node_id
        log.warning(msg)
        raise wz_exceptions.InternalServerError(msg)
    log.debug('User %s wants to PATCH %s node %s',
              authentication.current_user_id(), node_type, node_id)

    # Find the PATCH handler for the node type.
    try:
        patch_handler = custom.patch_handlers[node_type]
    except KeyError:
        log.info('No patch handler for node type %r', node_type)
        raise wz_exceptions.MethodNotAllowed('PATCH on node type %r not allowed' % node_type)

    # Let the PATCH handler do its thing.
    return patch_handler(node_id, patch)


def setup_app(app, url_prefix):
    app.register_blueprint(blueprint, url_prefix=url_prefix)
