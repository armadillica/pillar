"""Service accounts."""

import logging
import typing

import bson
import blinker
import bson

from flask import Blueprint, current_app, request
from werkzeug import exceptions as wz_exceptions

from pillar.api import local_auth
from pillar.api.utils import mongo
from pillar.api.utils import authorization, authentication, str2id, jsonify

blueprint = Blueprint('service', __name__)
log = logging.getLogger(__name__)
signal_user_changed_role = blinker.NamedSignal('badger:user_changed_role')

ROLES_WITH_GROUPS = {'admin', 'demo', 'subscriber'}

# Map of role name to group ID, for the above groups.
role_to_group_id = {}


class ServiceAccountCreationError(Exception):
    """Raised when a service account cannot be created."""


@blueprint.before_app_first_request
def fetch_role_to_group_id_map():
    """Fills the _role_to_group_id mapping upon application startup."""

    global role_to_group_id

    groups_coll = current_app.data.driver.db['groups']

    for role in ROLES_WITH_GROUPS:
        group = groups_coll.find_one({'name': role}, projection={'_id': 1})
        if group is None:
            log.warning('Group for role %r not found', role)
            continue
        role_to_group_id[role] = group['_id']

    log.debug('Group IDs for roles: %s', role_to_group_id)


@blueprint.route('/badger', methods=['POST'])
@authorization.require_login(require_roles={'service', 'badger'}, require_all=True)
def badger():
    if request.mimetype != 'application/json':
        log.debug('Received %s instead of application/json', request.mimetype)
        raise wz_exceptions.BadRequest()

    # Parse the request
    args = request.json
    action = args.get('action', '')
    user_email = args.get('user_email', '')
    role = args.get('role', '')

    current_user_id = authentication.current_user_id()
    log.info('Service account %s %ss role %r to/from user %s',
             current_user_id, action, role, user_email)

    users_coll = current_app.data.driver.db['users']

    # Check that the user is allowed to grant this role.
    srv_user = users_coll.find_one(current_user_id,
                                   projection={'service.badger': 1})
    if srv_user is None:
        log.error('badger(%s, %s, %s): current user %s not found -- how did they log in?',
                  action, user_email, role, current_user_id)
        return 'User not found', 403

    allowed_roles = set(srv_user.get('service', {}).get('badger', []))
    if role not in allowed_roles:
        log.warning('badger(%s, %s, %s): service account not authorized to %s role %s',
                    action, user_email, role, action, role)
        return 'Role not allowed', 403

    return do_badger(action, role=role, user_email=user_email)


def do_badger(action: str, *,
              role: str=None, roles: typing.Iterable[str]=None,
              user_email: str = '', user_id: bson.ObjectId = None):
    """Performs a badger action, returning a HTTP response.

    Either role or roles must be given.
    Either user_email or user_id must be given.
    """

    if action not in {'grant', 'revoke'}:
        log.error('do_badger(%r, %r, %r, %r): action %r not supported.',
                  action, role, user_email, user_id, action)
        raise wz_exceptions.BadRequest('Action %r not supported' % action)

    if not user_email and user_id is None:
        log.error('do_badger(%r, %r, %r, %r): neither email nor user_id given.',
                  action, role, user_email, user_id)
        raise wz_exceptions.BadRequest('User email not given')

    if bool(role) == bool(roles):
        log.error('do_badger(%r, role=%r, roles=%r, %r, %r): '
                  'either "role" or "roles" must be given.',
                  action, role, roles, user_email, user_id)
        raise wz_exceptions.BadRequest('Invalid role(s) given')

    # If only a single role was given, handle it as a set of one role.
    if not roles:
        roles = {role}
    del role

    users_coll = current_app.data.driver.db['users']

    # Fetch the user
    if user_email:
        query = {'email': user_email}
    else:
        query = user_id
    db_user = users_coll.find_one(query, projection={'roles': 1, 'groups': 1})
    if db_user is None:
        log.warning('badger(%s, roles=%s, user_email=%s, user_id=%s): user not found',
                    action, roles, user_email, user_id)
        return 'User not found', 404

    # Apply the action
    user_roles = set(db_user.get('roles') or [])
    if action == 'grant':
        user_roles |= roles
    else:
        user_roles -= roles

    groups = None
    for role in roles:
        groups = manage_user_group_membership(db_user, role, action)

        if groups is None:
            # No change for this role
            continue

        # Also update db_user for the next iteration.
        db_user['groups'] = groups

    updates = {'roles': list(user_roles)}
    if groups is not None:
        updates['groups'] = list(groups)

    log.debug('badger(%s, %s, user_email=%s, user_id=%s): applying updates %r',
              action, role, user_email, user_id, updates)
    users_coll.update_one({'_id': db_user['_id']},
                          {'$set': updates})

    # Let the rest of the world know this user was updated.
    db_user.update(updates)
    signal_user_changed_role.send(current_app, user=db_user)

    return '', 204


@blueprint.route('/urler/<project_id>', methods=['GET'])
@authorization.require_login(require_roles={'service', 'urler'}, require_all=True)
def urler(project_id):
    """Returns the URL of any project."""

    project_id = str2id(project_id)
    project = mongo.find_one_or_404('projects', project_id,
                                    projection={'url': 1})
    return jsonify({
        '_id': project_id,
        'url': project['url']})


def manage_user_group_membership(db_user, role, action):
    """Some roles have associated groups; this function maintains group & role membership.

    Does NOT alter the given user, nor the database.

    :return: the new groups of the user, or None if the groups shouldn't be changed.
    :rtype: set
    """

    if action not in {'grant', 'revoke'}:
        raise ValueError('Action %r not supported' % action)

    # Currently only three roles have associated groups.
    if role not in ROLES_WITH_GROUPS:
        return

    # Find the group
    try:
        group_id = role_to_group_id[role]
    except KeyError:
        log.warning('Group for role %r cannot be found, unable to %s membership for user %s',
                    role, action, db_user['_id'])
        return

    user_groups = set(db_user.get('groups') or [])
    if action == 'grant':
        user_groups.add(group_id)
    else:
        user_groups.discard(group_id)

    return user_groups


def create_service_account(email: str, roles: typing.Iterable, service: dict,
                           *, full_name: str=None):
    """Creates a service account with the given roles + the role 'service'.

    :param email: optional email address associated with the account.
    :param roles: iterable of role names
    :param service: dict of the 'service' key in the user.
    :param full_name: Full name of the service account. If None, will be set to
        something reasonable.

    :return: tuple (user doc, token doc)
    """

    # Create a user with the correct roles.
    roles = sorted(set(roles).union({'service'}))
    user_id = bson.ObjectId()

    log.info('Creating service account %s with roles %s', user_id, roles)
    user = {'_id': user_id,
            'username': f'SRV-{user_id}',
            'groups': [],
            'roles': roles,
            'settings': {'email_communications': 0},
            'auth': [],
            'full_name': full_name or f'SRV-{user_id}',
            'service': service}
    if email:
        user['email'] = email
    result, _, _, status = current_app.post_internal('users', user)

    if status != 201:
        raise ServiceAccountCreationError('Error creating user {}: {}'.format(user_id, result))
    user.update(result)

    # Create an authentication token that won't expire for a long time.
    token = generate_auth_token(user['_id'])

    return user, token


def generate_auth_token(service_account_id) -> dict:
    """Generates an authentication token for a service account."""

    token_info = local_auth.generate_and_store_token(service_account_id, days=36500, prefix=b'SRV')
    return token_info


def setup_app(app, api_prefix):
    app.register_api_blueprint(blueprint, url_prefix=api_prefix)
