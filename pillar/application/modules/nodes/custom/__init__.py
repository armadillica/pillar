import logging

log = logging.getLogger(__name__)
patch_handlers = {}  # mapping from node type to callable.


def register_patch_handler(node_type):
    """Decorator, registers the decorated function as patch handler for the given node type."""

    def wrapper(func):
        if node_type in patch_handlers:
            raise ValueError('Node type %r already handled by %r' %
                             (node_type, patch_handlers[node_type]))

        log.debug('Registering %s as PATCH handler for node type %r',
                  func, node_type)
        patch_handlers[node_type] = func
        return func

    return wrapper
