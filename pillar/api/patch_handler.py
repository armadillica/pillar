"""Handler for PATCH requests.

This supports PATCH request in the sense described by William Durand:
http://williamdurand.fr/2014/02/14/please-do-not-patch-like-an-idiot/

Each PATCH should be a JSON dict with at least a key 'op' with the
name of the operation to perform.
"""

import logging

import flask

from pillar.api.utils import authorization

log = logging.getLogger(__name__)


class AbstractPatchHandler:
    """Abstract PATCH handler supporting multiple operations.

    Each operation, i.e. possible value of the 'op' key in the PATCH body,
    should be matched to a similarly named "patch_xxx" function in a subclass.
    For example, the operation "set-owner" is mapped to "patch_set_owner".

    :cvar route: the Flask/Werkzeug route to attach this handler to.
        For most handlers, the default will be fine.
    :cvar item_name: the name of the things to patch, like "job", "task" etc.
        Only used for logging.
    """

    route: str = '/<object_id>'
    item_name: str = None

    def __init_subclass__(cls, **kwargs):
        if not cls.route:
            raise ValueError('Subclass must set route')
        if not cls.item_name:
            raise ValueError('Subclass must set item_name')

    def __init__(self, blueprint: flask.Blueprint):
        self.log: logging.Logger = log.getChild(self.__class__.__name__)
        self.patch_handlers = {
            name[6:].replace('_', '-'): getattr(self, name)
            for name in dir(self)
            if name.startswith('patch_') and callable(getattr(self, name))
        }

        if self.log.isEnabledFor(logging.INFO):
            self.log.info('Creating PATCH handler %s%s for operations: %s',
                          blueprint.name, self.route,
                          sorted(self.patch_handlers.keys()))

        blueprint.add_url_rule(self.route,
                               self.patch.__name__,
                               self.patch,
                               methods=['PATCH'])

    @authorization.require_login()
    def patch(self, object_id: str):
        from flask import request
        import werkzeug.exceptions as wz_exceptions
        from pillar.api.utils import str2id, authentication

        # Parse the request
        real_object_id = str2id(object_id)
        patch = request.get_json()
        if not patch:
            raise wz_exceptions.BadRequest('Patch must contain JSON')

        try:
            patch_op = patch['op']
        except KeyError:
            raise wz_exceptions.BadRequest("PATCH should contain 'op' key to denote operation.")

        log.debug('User %s wants to PATCH "%s" %s %s',
                  authentication.current_user_id(), patch_op, self.item_name, real_object_id)

        # Find the PATCH handler for the operation.
        try:
            handler = self.patch_handlers[patch_op]
        except KeyError:
            log.warning('No %s PATCH handler for operation %r', self.item_name, patch_op)
            raise wz_exceptions.BadRequest('Operation %r not supported' % patch_op)

        # Let the PATCH handler do its thing.
        response = handler(real_object_id, patch)
        if response is None:
            return '', 204
        return response
