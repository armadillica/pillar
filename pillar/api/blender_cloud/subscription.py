import logging
import typing

from flask import Blueprint, Response
import requests
from requests.adapters import HTTPAdapter

from pillar import auth, current_app
from pillar.api import blender_id
from pillar.api.utils import authorization, jsonify
from pillar.auth import current_user

log = logging.getLogger(__name__)
blueprint = Blueprint('blender_cloud.subscription', __name__)

# Mapping from roles on Blender ID to roles here in Pillar.
# Roles not mentioned here will not be synced from Blender ID.
ROLES_BID_TO_PILLAR = {
    'cloud_subscriber': 'subscriber',
    'cloud_demo': 'demo',
    'cloud_has_subscription': 'has_subscription',
}


@blueprint.route('/update-subscription')
@authorization.require_login()
def update_subscription() -> typing.Tuple[str, int]:
    """Updates the subscription status of the current user.

    Returns an empty HTTP response.
    """

    my_log: logging.Logger = log.getChild('update_subscription')
    current_user = auth.get_current_user()

    try:
        bid_user = blender_id.fetch_blenderid_user()
    except blender_id.LogoutUser:
        auth.logout_user()
        return '', 204

    if not bid_user:
        my_log.warning('Logged in user %s has no BlenderID account! '
                       'Unable to update subscription status.', current_user.user_id)
        return '', 204

    do_update_subscription(current_user, bid_user)
    return '', 204


@blueprint.route('/update-subscription-for/<user_id>', methods=['POST'])
@authorization.require_login(require_cap='admin')
def update_subscription_for(user_id: str):
    """Updates the user based on their info at Blender ID."""

    from urllib.parse import urljoin

    from pillar.api.utils import str2id

    my_log = log.getChild('update_subscription_for')

    bid_session = requests.Session()
    bid_session.mount('https://', HTTPAdapter(max_retries=5))
    bid_session.mount('http://', HTTPAdapter(max_retries=5))

    users_coll = current_app.db('users')
    db_user = users_coll.find_one({'_id': str2id(user_id)})
    if not db_user:
        my_log.warning('User %s not found in database', user_id)
        return Response(f'User {user_id} not found in our database', status=404)

    log.info('Updating user %s from Blender ID on behalf of %s',
             db_user['email'], current_user.email)

    bid_user_id = blender_id.get_user_blenderid(db_user)
    if not bid_user_id:
        my_log.info('User %s has no Blender ID', user_id)
        return Response('User has no Blender ID', status=404)

    # Get the user info from Blender ID, and handle errors.
    api_url = current_app.config['BLENDER_ID_USER_INFO_API']
    api_token = current_app.config['BLENDER_ID_USER_INFO_TOKEN']
    url = urljoin(api_url, bid_user_id)
    resp = bid_session.get(url, headers={'Authorization': f'Bearer {api_token}'})
    if resp.status_code == 404:
        my_log.info('User %s has a Blender ID %s but Blender ID itself does not find it',
                    user_id, bid_user_id)
        return Response(f'User {bid_user_id} does not exist at Blender ID', status=404)
    if resp.status_code != 200:
        my_log.info('Error code %s getting user %s from Blender ID (resp = %s)',
                    resp.status_code, user_id, resp.text)
        return Response(f'Error code {resp.status_code} from Blender ID', status=resp.status_code)

    # Update the user in our database.
    local_user = auth.UserClass.construct('', db_user)
    bid_user = resp.json()
    do_update_subscription(local_user, bid_user)

    return '', 204


def do_update_subscription(local_user: auth.UserClass, bid_user: dict):
    """Updates the subscription status of the user given the Blender ID user info.

    Uses the badger service to update the user's roles from Blender ID.

    bid_user should be a dict like:
    {'id': 1234,
     'full_name': 'मूंगफली मक्खन प्रेमी',
     'email': 'here@example.com',
     'roles': {'cloud_demo': True}}

    The 'roles' key can also be an interable of role names instead of a dict.
    """

    from pillar.api import service

    my_log: logging.Logger = log.getChild('do_update_subscription')

    try:
        email = bid_user['email']
    except KeyError:
        email = '-missing email-'

    # Transform the BID roles from a dict to a set.
    bidr = bid_user.get('roles', set())
    if isinstance(bidr, dict):
        bid_roles = {role
                     for role, has_role in bid_user.get('roles', {}).items()
                     if has_role}
    else:
        bid_roles = set(bidr)

    # Handle the role changes via the badger service functionality.
    plr_roles = set(local_user.roles)

    grant_roles = set()
    revoke_roles = set()
    for bid_role, plr_role in ROLES_BID_TO_PILLAR.items():
        if bid_role in bid_roles and plr_role not in plr_roles:
            grant_roles.add(plr_role)
            continue
        if bid_role not in bid_roles and plr_role in plr_roles:
            revoke_roles.add(plr_role)

    user_id = local_user.user_id

    if grant_roles:
        if my_log.isEnabledFor(logging.INFO):
            my_log.info('granting roles to user %s (Blender ID %s): %s',
                        user_id, email, ', '.join(sorted(grant_roles)))
        service.do_badger('grant', roles=grant_roles, user_id=user_id)

    if revoke_roles:
        if my_log.isEnabledFor(logging.INFO):
            my_log.info('revoking roles to user %s (Blender ID %s): %s',
                        user_id, email, ', '.join(sorted(revoke_roles)))
        service.do_badger('revoke', roles=revoke_roles, user_id=user_id)

    # Re-index the user in the search database.
    from pillar.api.users import hooks
    hooks.push_updated_user_to_algolia({'_id': user_id}, {})


def setup_app(app, url_prefix):
    log.info('Registering blueprint at %s', url_prefix)
    app.register_api_blueprint(blueprint, url_prefix=url_prefix)
