import collections
import logging
import typing

from flask import Blueprint

from pillar.auth import UserClass
from pillar.api.utils import authorization

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

    from pillar import auth
    from pillar.api import blender_id

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


def do_update_subscription(local_user: UserClass, bid_user: dict):
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


def setup_app(app, url_prefix):
    log.info('Registering blueprint at %s', url_prefix)
    app.register_api_blueprint(blueprint, url_prefix=url_prefix)
