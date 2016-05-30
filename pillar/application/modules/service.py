"""Service accounts."""

import logging

from bson import ObjectId
from flask import Blueprint, current_app, g, request
from werkzeug import exceptions as wz_exceptions

from application.utils import authorization
from application.modules import local_auth

blueprint = Blueprint('service', __name__)
log = logging.getLogger(__name__)


@blueprint.route('/badger', methods=['POST'])
@authorization.require_login(require_roles={u'service', u'badger'}, require_all=True)
def badger():
    if request.mimetype != 'application/json':
        raise wz_exceptions.BadRequest()

    # Parse the request
    args = request.json
    action = args['action']
    user_email = args['user_email']
    role = args['role']

    if action not in {'grant', 'revoke'}:
        raise wz_exceptions.BadRequest('Action %r not supported' % action)

    log.info('Service account %s %ss role %r to/from user %s',
             g.current_user['user_id'], action, role, user_email)

    users_coll = current_app.data.driver.db['users']

    # Check that the user is allowed to grant this role.
    srv_user = users_coll.find_one(g.current_user['user_id'],
                                   projection={'service.badger': 1})
    if srv_user is None:
        log.error('badger(%s, %s, %s): current user %s not found -- how did they log in?',
                  action, user_email, role, g.current_user['user_id'])
        return 'User not found', 403

    allowed_roles = set(srv_user.get('service', {}).get('badger', []))
    if role not in allowed_roles:
        log.warning('badger(%s, %s, %s): service account not authorized to %s role %s',
                    action, user_email, role, action, role)
        return 'Role not allowed', 403

    # Fetch the user
    db_user = users_coll.find_one({'email': user_email}, projection={'roles': 1})
    if db_user is None:
        log.warning('badger(%s, %s, %s): user not found', action, user_email, role)
        return 'User not found', 404

    # Apply the action
    roles = set(db_user['roles'] or [])
    if action == 'grant':
        roles.add(role)
    else:
        roles.discard(role)
    users_coll.update_one({'_id': db_user['_id']},
                          {'$set': {'roles': list(roles)}})

    return '', 204


def create_service_account(email, roles, service):
    """Creates a service account with the given roles + the role 'service'.

    :param email: email address associated with the account
    :type email: str
    :param roles: iterable of role names
    :param service: dict of the 'service' key in the user.
    :type service: dict
    :return: tuple (user doc, token doc)
    """
    from eve.methods.post import post_internal

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
    result, _, _, status = post_internal('users', user)
    if status != 201:
        raise SystemExit('Error creating user {}: {}'.format(email, result))
    user.update(result)

    # Create an authentication token that won't expire for a long time.
    token = local_auth.generate_and_store_token(user['_id'], days=36500, prefix='SRV')

    return user, token


def setup_app(app, url_prefix):
    app.register_blueprint(blueprint, url_prefix=url_prefix)
