import logging
import functools
from flask import g
from flask import abort
from application import app

log = logging.getLogger(__name__)


def check_permissions(resource, method, append_allowed_methods=False):
    """Check user permissions to access a node. We look up node permissions from
    world to groups to users and match them with the computed user permissions.
    If there is not match, we raise 403.
    """
    if method != 'GET' and append_allowed_methods:
        raise ValueError("append_allowed_methods only allowed with 'GET' method")

    current_user = g.current_user

    if 'permissions' in resource:
        # If permissions are embedded in the node (this overrides any other
        # matching permission originally set at node_type level)
        resource_permissions = resource['permissions']
    else:
        resource_permissions = {}
    if 'node_type' in resource:
        if type(resource['node_type']) is dict:
            # If the node_type is embedded in the document, extract permissions
            # from there
            computed_permissions = resource['node_type']['permissions']
        else:
            # If the node_type is referenced with an ObjectID (was not embedded
            # on request) query for if from the database and get the permissions

            # node_types_collection = app.data.driver.db['node_types']
            # node_type = node_types_collection.find_one(resource['node_type'])

            if type(resource['project']) is dict:
                project = resource['project']
            else:
                projects_collection = app.data.driver.db['projects']
                project = projects_collection.find_one(resource['project'])
            node_type = next(
                (item for item in project['node_types'] if item.get('name') \
                 and item['name'] == resource['node_type']), None)
            computed_permissions = node_type['permissions']
    else:
        computed_permissions = {}

    # Override computed_permissions if override is provided
    computed_permissions.update(resource_permissions)

    if not computed_permissions:
        log.info('No permissions available to compute for %s on resource %r',
                 method, resource.get('node_type', resource))
        abort(403)

    # Accumulate allowed methods from the user, group and world level.
    allowed_methods = set()

    if current_user:
        # If the user is authenticated, proceed to compare the group permissions
        for permission in computed_permissions['groups']:
            if permission['group'] in current_user['groups']:
                allowed_methods.update(permission['methods'])

        for permission in computed_permissions['users']:
            if current_user['user_id'] == permission['user']:
                allowed_methods.update(permission['methods'])

    # Check if the node is public or private. This must be set for non logged
    # in users to see the content. For most BI projects this is on by default,
    # while for private project this will not be set at all.
    if 'world' in computed_permissions:
        allowed_methods.update(computed_permissions['world'])

    permission_granted = method in allowed_methods
    if permission_granted:
        if append_allowed_methods:
            resource['allowed_methods'] = list(set(allowed_methods))
        return

    abort(403)


def require_login(require_roles=set()):
    """Decorator that enforces users to authenticate.

    Optionally only allows access to users with a certain role./
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_user = g.get('current_user')

            if current_user is None:
                log.warning('Unauthenticated acces to %s attempted.', func)
                abort(403)

            if require_roles and not require_roles.intersection(set(current_user['roles'])):
                log.warning('User %s is authenticated, but does not have any required role %s to '
                            'access %s', current_user['user_id'], require_roles, func)
                abort(403)

            return func(*args, **kwargs)
        return wrapper
    return decorator


def user_has_role(role):
    """Returns True iff the user is logged in and has the given role."""

    current_user = g.get('current_user')
    if current_user is None:
        return False

    return role in current_user['roles']
