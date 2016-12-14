"""Service accounts."""

import logging

import blinker
from flask import Blueprint, current_app, request
from pillar.api import local_auth
from pillar.api.utils import mongo
from pillar.api.utils import authorization, authentication, str2id, jsonify
from werkzeug import exceptions as wz_exceptions

blueprint = Blueprint('service', __name__)
log = logging.getLogger(__name__)
signal_user_changed_role = blinker.NamedSignal('badger:user_changed_role')

ROLES_WITH_GROUPS = {u'admin', u'demo', u'subscriber'}

# Map of role name to group ID, for the above groups.
role_to_group_id = {}


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
@authorization.require_login(require_roles={u'service', u'badger'}, require_all=True)
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

    return do_badger(action, user_email, role)


def do_badger(action, user_email, role):
    """Performs a badger action, returning a HTTP response."""

    if action not in {'grant', 'revoke'}:
        raise wz_exceptions.BadRequest('Action %r not supported' % action)

    if not user_email:
        raise wz_exceptions.BadRequest('User email not given')

    if not role:
        raise wz_exceptions.BadRequest('Role not given')

    users_coll = current_app.data.driver.db['users']

    # Fetch the user
    db_user = users_coll.find_one({'email': user_email}, projection={'roles': 1, 'groups': 1})
    if db_user is None:
        log.warning('badger(%s, %s, %s): user not found', action, user_email, role)
        return 'User not found', 404

    # Apply the action
    roles = set(db_user.get('roles') or [])
    if action == 'grant':
        roles.add(role)
    else:
        roles.discard(role)

    groups = manage_user_group_membership(db_user, role, action)

    updates = {'roles': list(roles)}
    if groups is not None:
        updates['groups'] = list(groups)

    users_coll.update_one({'_id': db_user['_id']},
                          {'$set': updates})

    # Let the rest of the world know this user was updated.
    db_user.update(updates)
    signal_user_changed_role.send(current_app, user=db_user)

    return '', 204


@blueprint.route('/urler/<project_id>', methods=['GET'])
@authorization.require_login(require_roles={u'service', u'urler'}, require_all=True)
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


def create_service_account(email, roles, service, update_existing=None):
    """Creates a service account with the given roles + the role 'service'.

    :param email: email address associated with the account
    :type email: str
    :param roles: iterable of role names
    :param service: dict of the 'service' key in the user.
    :type service: dict
    :param update_existing: callback function that receives an existing user to update
        for this service, in case the email address is already in use by someone.
        If not given or None, updating existing users is disallowed, and a ValueError
        exception is thrown instead.

    :return: tuple (user doc, token doc)
    """

    from pillar.api.utils import remove_private_keys

    # Find existing
    users_coll = current_app.db()['users']
    user = users_coll.find_one({'email': email})
    if user:
        # Check whether updating is allowed at all.
        if update_existing is None:
            raise ValueError('User %s already exists' % email)

        # Compute the new roles, and assign.
        roles = list(set(roles).union({u'service'}).union(user['roles']))
        user['roles'] = list(roles)

        # Let the caller perform any required updates.
        log.info('Updating existing user %s to become service account for %s',
                 email, roles)
        update_existing(user['service'])

        # Try to store the updated user.
        result, _, _, status = current_app.put_internal('users',
                                                        remove_private_keys(user),
                                                        _id=user['_id'])
        expected_status = 200
    else:
        # Create a user with the correct roles.
        roles = list(set(roles).union({u'service'}))
        user = {'username': email,
                'groups': [],
                'roles': roles,
                'settings': {'email_communications': 0},
                'auth': [],
                'full_name': email,
                'email': email,
                'service': service}
        result, _, _, status = current_app.post_internal('users', user)
        expected_status = 201

    if status != expected_status:
        raise SystemExit('Error creating user {}: {}'.format(email, result))
    user.update(result)

    # Create an authentication token that won't expire for a long time.
    token = local_auth.generate_and_store_token(user['_id'], days=36500, prefix='SRV')

    return user, token


def setup_app(app, api_prefix):
    app.register_api_blueprint(blueprint, url_prefix=api_prefix)
