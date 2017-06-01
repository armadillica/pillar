import copy
import json

from eve.utils import parse_request
from flask import current_app, g
from pillar.api.users.routes import log
from pillar.api.utils.authorization import user_has_role
from werkzeug import exceptions as wz_exceptions

USER_EDITABLE_FIELDS = {'full_name', 'username', 'email', 'settings'}

# These fields nobody is allowed to touch directly, not even admins.
USER_ALWAYS_RESTORE_FIELDS = {'auth'}


def before_replacing_user(request, lookup):
    """Prevents changes to any field of the user doc, except USER_EDITABLE_FIELDS."""

    # Find the user that is being replaced
    req = parse_request('users')
    req.projection = json.dumps({key: 0 for key in USER_EDITABLE_FIELDS})
    original = current_app.data.find_one('users', req, **lookup)

    # Make sure that the replacement has a valid auth field.
    put_data = request.get_json()

    # We should get a ref to the cached JSON, and not a copy. This will allow us to
    # modify the cached JSON so that Eve sees our modifications.
    assert put_data is request.get_json()

    # Reset fields that shouldn't be edited to their original values. This is only
    # needed when users are editing themselves; admins are allowed to edit much more.
    if not user_has_role('admin'):
        for db_key, db_value in original.items():
            if db_key[0] == '_' or db_key in USER_EDITABLE_FIELDS:
                continue

            if db_key in original:
                put_data[db_key] = copy.deepcopy(original[db_key])

        # Remove fields added by this PUT request, except when they are user-editable.
        for put_key in list(put_data.keys()):
            if put_key[0] == '_' or put_key in USER_EDITABLE_FIELDS:
                continue

            if put_key not in original:
                del put_data[put_key]

    # Always restore those fields
    for db_key in USER_ALWAYS_RESTORE_FIELDS:
        if db_key in original:
            put_data[db_key] = copy.deepcopy(original[db_key])
        else:
            del put_data[db_key]

    # Regular users should always have an email address
    if 'service' not in put_data['roles']:
        if not put_data.get('email'):
            raise wz_exceptions.UnprocessableEntity('email field must be given')


def push_updated_user_to_algolia(user, original):
    """Push an update to the Algolia index when a user item is updated"""

    from pillar.celery import algolia_tasks

    algolia_tasks.push_updated_user_to_algolia.delay(str(user['_id']))


def send_blinker_signal_roles_changed(user, original):
    """Sends a Blinker signal that the user roles were changed, so others can respond."""

    if user.get('roles') == original.get('roles'):
        return

    from pillar.api.service import signal_user_changed_role

    log.info('User %s changed roles to %s, sending Blinker signal',
             user.get('_id'), user.get('roles'))
    signal_user_changed_role.send(current_app, user=user)


def check_user_access(request, lookup):
    """Modifies the lookup dict to limit returned user info."""

    # No access when not logged in.
    current_user = g.get('current_user')
    current_user_id = current_user['user_id'] if current_user else None

    # Admins can do anything and get everything, except the 'auth' block.
    if user_has_role('admin'):
        return

    if not lookup and not current_user:
        raise wz_exceptions.Forbidden()

    # Add a filter to only return the current user.
    if '_id' not in lookup:
        lookup['_id'] = current_user['user_id']


def check_put_access(request, lookup):
    """Only allow PUT to the current user, or all users if admin."""

    if user_has_role('admin'):
        return

    current_user = g.get('current_user')
    if not current_user:
        raise wz_exceptions.Forbidden()

    if str(lookup['_id']) != str(current_user['user_id']):
        raise wz_exceptions.Forbidden()


def after_fetching_user(user):
    # Deny access to auth block; authentication stuff is managed by
    # custom end-points.
    user.pop('auth', None)

    current_user = g.get('current_user')
    current_user_id = current_user['user_id'] if current_user else None

    # Admins can do anything and get everything, except the 'auth' block.
    if user_has_role('admin'):
        return

    # Only allow full access to the current user.
    if str(user['_id']) == str(current_user_id):
        return

    # Remove all fields except public ones.
    public_fields = {'full_name', 'username', 'email'}
    for field in list(user.keys()):
        if field not in public_fields:
            del user[field]


def after_fetching_user_resource(response):
    for user in response['_items']:
        after_fetching_user(user)


def post_GET_user(request, payload):
    json_data = json.loads(payload.data)
    # Check if we are querying the users endpoint (instead of the single user)
    if json_data.get('_id') is None:
        return
    # json_data['computed_permissions'] = \
    #     compute_permissions(json_data['_id'], app.data.driver)
    payload.data = json.dumps(json_data)
