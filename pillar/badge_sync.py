import collections
import datetime
import logging
import typing
from urllib.parse import urljoin

import bson
import requests

from pillar import current_app, auth
from pillar.api.utils import utcnow

SyncUser = collections.namedtuple('SyncUser', 'user_id token bid_user_id')
BadgeHTML = collections.namedtuple('BadgeHTML', 'html expires')
log = logging.getLogger(__name__)


class StopRefreshing(Exception):
    """Indicates that Blender ID is having problems.

    Further badge refreshes should be put on hold to avoid bludgeoning
    a suffering Blender ID.
    """


def find_user_to_sync(user_id: bson.ObjectId) -> typing.Optional[SyncUser]:
    """Return user information for syncing badges for a specific user.

    Returns None if the user cannot be synced (no 'badge' scope on a token,
    or no Blender ID user_id known).
    """
    my_log = log.getChild('refresh_single_user')

    now = utcnow()
    tokens_coll = current_app.db('tokens')
    users_coll = current_app.db('users')

    token_info = tokens_coll.find_one({
        'user': user_id,
        'token': {'$exists': True},
        'oauth_scopes': 'badge',
        'expire_time': {'$gt': now},
    })
    if not token_info:
        my_log.debug('No token with scope "badge" for user %s', user_id)
        return None

    user_info = users_coll.find_one({'_id': user_id})
    # TODO(Sybren): do this filtering in the MongoDB query:
    bid_user_ids = [auth_info.get('user_id')
                    for auth_info in user_info.get('auth', [])
                    if auth_info.get('provider', '') == 'blender-id' and auth_info.get('user_id')]
    if not bid_user_ids:
        my_log.debug('No Blender ID user_id for user %s', user_id)
        return None

    bid_user_id = bid_user_ids[0]
    return SyncUser(user_id=user_id, token=token_info['token'], bid_user_id=bid_user_id)


def find_users_to_sync() -> typing.Iterable[SyncUser]:
    """Return user information of syncable users with badges."""

    now = utcnow()
    tokens_coll = current_app.db('tokens')
    cursor = tokens_coll.aggregate([
        # Find all users who have a 'badge' scope in their OAuth token.
        {'$match': {
            'token': {'$exists': True},
            'oauth_scopes': 'badge',
            'expire_time': {'$gt': now},
            # TODO(Sybren): save real token expiry time but keep checking tokens hourly when they are used!
        }},
        {'$lookup': {
            'from': 'users',
            'localField': 'user',
            'foreignField': '_id',
            'as': 'user'
        }},

        # Prevent 'user' from being an array.
        {'$unwind': {'path': '$user'}},

        # Get the Blender ID user ID only.
        {'$unwind': {'path': '$user.auth'}},
        {'$match': {'user.auth.provider': 'blender-id'}},

        # Only select those users whose badge doesn't exist or has expired.
        {'$match': {
            'user.badges.expires': {'$not': {'$gt': now}}
        }},

        # Make sure that the badges that expire last are also refreshed last.
        {'$sort': {'user.badges.expires': 1}},

        # Reduce the document to the info we're after.
        {'$project': {
            'token': True,
            'user._id': True,
            'user.auth.user_id': True,
        }},
    ])

    log.debug('Aggregating tokens and users')
    for user_info in cursor:
        log.debug('User %s has badges %s',
                  user_info['user']['_id'], user_info['user'].get('badges'))
        yield SyncUser(
            user_id=user_info['user']['_id'],
            token=user_info['token'],
            bid_user_id=user_info['user']['auth']['user_id'])


def fetch_badge_html(session: requests.Session, user: SyncUser, size: str) \
        -> str:
    """Fetch a Blender ID badge for this user.

    :param session:
    :param user:
    :param size: Size indication for the badge images, see the Blender ID
        documentation/code. As of this writing valid sizes are {'s', 'm', 'l'}.
    """
    my_log = log.getChild('fetch_badge_html')

    blender_id_endpoint = current_app.config['BLENDER_ID_ENDPOINT']
    url = urljoin(blender_id_endpoint, f'api/badges/{user.bid_user_id}/html/{size}')

    my_log.debug('Fetching badge HTML at %s for user %s', url, user.user_id)
    try:
        resp = session.get(url, headers={'Authorization': f'Bearer {user.token}'})
    except requests.ConnectionError as ex:
        my_log.warning('Unable to connect to Blender ID at %s: %s', url, ex)
        raise StopRefreshing()

    if resp.status_code == 204:
        my_log.debug('No badges for user %s', user.user_id)
        return ''
    if resp.status_code == 403:
        # TODO(Sybren): this indicates the token is invalid, so we could just as well delete it.
        my_log.warning('Tried fetching %s for user %s but received a 403: %s',
                       url, user.user_id, resp.text)
        return ''
    if resp.status_code == 400:
        my_log.warning('Blender ID did not accept our GET request at %s for user %s: %s',
                       url, user.user_id, resp.text)
        return ''
    if resp.status_code == 500:
        my_log.warning('Blender ID returned an internal server error on %s for user %s, '
                       'aborting all badge refreshes: %s', url, user.user_id, resp.text)
        raise StopRefreshing()
    if resp.status_code == 404:
        my_log.warning('Blender ID has no user %s for our user %s', user.bid_user_id, user.user_id)
        return ''
    resp.raise_for_status()
    return resp.text


def refresh_all_badges(only_user_id: typing.Optional[bson.ObjectId] = None, *,
                       dry_run=False,
                       timelimit: datetime.timedelta):
    """Re-fetch all badges for all users, except when already refreshed recently.

    :param only_user_id: Only refresh this user. This is expected to be used
        sparingly during manual maintenance / debugging sessions only. It does
        fetch all users to refresh, and in Python code skips all except the
        given one.
    :param dry_run: if True the changes are described in the log, but not performed.
    :param timelimit: Refreshing will stop after this time. This allows for cron(-like)
        jobs to run without overlapping, even when the number fo badges to refresh
        becomes larger than possible within the period of the cron job.
    """
    my_log = log.getChild('refresh_all_badges')

    # Test the config before we start looping over the world.
    badge_expiry = badge_expiry_config()
    if not badge_expiry or not isinstance(badge_expiry, datetime.timedelta):
        raise ValueError('BLENDER_ID_BADGE_EXPIRY not configured properly, should be a timedelta')

    session = _get_requests_session()
    deadline = utcnow() + timelimit

    num_updates = 0
    for user_info in find_users_to_sync():
        if utcnow() > deadline:
            my_log.info('Stopping badge refresh because the timelimit %s (H:MM:SS) was hit.',
                        timelimit)
            break

        if only_user_id and user_info.user_id != only_user_id:
            my_log.debug('Skipping user %s', user_info.user_id)
            continue
        try:
            badge_html = fetch_badge_html(session, user_info, 's')
        except StopRefreshing:
            my_log.error('Blender ID has internal problems, stopping badge refreshing at user %s',
                         user_info)
            break

        num_updates += 1
        update_badges(user_info, badge_html, badge_expiry, dry_run=dry_run)
    my_log.info('Updated badges of %d users%s', num_updates, ' (dry-run)' if dry_run else '')


def _get_requests_session() -> requests.Session:
    from requests.adapters import HTTPAdapter
    session = requests.Session()
    session.mount('https://', HTTPAdapter(max_retries=5))
    return session


def refresh_single_user(user_id: bson.ObjectId):
    """Refresh badges for a single user."""
    my_log = log.getChild('refresh_single_user')

    badge_expiry = badge_expiry_config()
    if not badge_expiry:
        my_log.warning('Skipping badge fetching, BLENDER_ID_BADGE_EXPIRY not configured')

    my_log.debug('Fetching badges for user %s', user_id)
    session = _get_requests_session()
    user_info = find_user_to_sync(user_id)
    if not user_info:
        return

    try:
        badge_html = fetch_badge_html(session, user_info, 's')
    except StopRefreshing:
        my_log.error('Blender ID has internal problems, stopping badge refreshing at user %s',
                     user_info)
        return

    update_badges(user_info, badge_html, badge_expiry, dry_run=False)
    my_log.info('Updated badges of user %s', user_id)


def update_badges(user_info: SyncUser, badge_html: str, badge_expiry: datetime.timedelta,
                  *, dry_run: bool):
    my_log = log.getChild('update_badges')
    users_coll = current_app.db('users')

    update = {'badges': {
        'html': badge_html,
        'expires': utcnow() + badge_expiry,
    }}
    my_log.info('Updating badges HTML for Blender ID %s, user %s',
                user_info.bid_user_id, user_info.user_id)

    if dry_run:
        return

    result = users_coll.update_one({'_id': user_info.user_id},
                                   {'$set': update})
    if result.matched_count != 1:
        my_log.warning('Unable to update badges for user %s', user_info.user_id)


def badge_expiry_config() -> datetime.timedelta:
    return current_app.config.get('BLENDER_ID_BADGE_EXPIRY')


@auth.user_logged_in.connect
def sync_badge_upon_login(sender: auth.UserClass, **kwargs):
    """Auto-sync badges when a user logs in."""

    log.info('Refreshing badge of %s because they logged in', sender.user_id)
    refresh_single_user(sender.user_id)
