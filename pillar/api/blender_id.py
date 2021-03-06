"""Blender ID subclient endpoint.

Also contains functionality for other parts of Pillar to perform communication
with Blender ID.
"""

import datetime
import logging
from urllib.parse import urljoin

import requests
from bson import tz_util
from rauth import OAuth2Session
from flask import Blueprint, request, jsonify, session
from requests.adapters import HTTPAdapter
import urllib3.util.retry

from pillar import current_app
from pillar.auth import get_blender_id_oauth_token
from pillar.api.utils import authentication, utcnow
from pillar.api.utils.authentication import find_user_in_db, upsert_user

blender_id = Blueprint('blender_id', __name__)
log = logging.getLogger(__name__)


class LogoutUser(Exception):
    """Raised when Blender ID tells us the current user token is invalid.

    This indicates the user should be immediately logged out.
    """


class Session(requests.Session):
    """Requests Session suitable for Blender ID communication."""

    def __init__(self):
        super().__init__()

        retries = urllib3.util.retry.Retry(
            total=10,
            backoff_factor=0.05,
        )
        http_adapter = requests.adapters.HTTPAdapter(max_retries=retries)

        self.mount('https://', http_adapter)
        self.mount('http://', http_adapter)

    def authenticate(self):
        """Attach the current user's authentication token to the request."""
        bid_token = get_blender_id_oauth_token()
        if not bid_token:
            raise TypeError('authenticate() requires current user to be logged in with Blender ID')

        self.headers['Authorization'] = f'Bearer {bid_token}'


@blender_id.route('/store_scst', methods=['POST'])
def store_subclient_token():
    """Verifies & stores a user's subclient-specific token."""

    user_id = request.form['user_id']  # User ID at BlenderID
    subclient_id = request.form['subclient_id']
    scst = request.form['token']

    db_user, status = validate_create_user(user_id, scst, subclient_id)

    if db_user is None:
        log.warning('Unable to verify subclient token with Blender ID.')
        return jsonify({'status': 'fail',
                        'error': 'BLENDER ID ERROR'}), 403

    return jsonify({'status': 'success',
                    'subclient_user_id': str(db_user['_id'])}), status


def validate_create_user(blender_id_user_id, token, oauth_subclient_id):
    """Validates a user against Blender ID, creating the user in our database.

    :param blender_id_user_id: the user ID at the BlenderID server.
    :param token: the OAuth access token.
    :param oauth_subclient_id: the subclient ID, or empty string if not a subclient.
    :returns: (user in MongoDB, HTTP status 200 or 201)
    """

    # Verify with Blender ID
    log.debug('Storing token for BlenderID user %s', blender_id_user_id)
    user_info, token_expiry = validate_token(blender_id_user_id, token, oauth_subclient_id)

    if user_info is None:
        log.debug('Unable to verify token with Blender ID.')
        return None, None

    # Blender ID can be queried without user ID, and will always include the
    # correct user ID in its response.
    log.debug('Obtained user info from Blender ID: %s', user_info)

    # Store the user info in MongoDB.
    db_user = find_user_in_db(user_info)
    db_id, status = upsert_user(db_user)

    # Store the token in MongoDB.
    ip_based_roles = current_app.org_manager.roles_for_request()
    authentication.store_token(db_id, token, token_expiry, oauth_subclient_id,
                               org_roles=ip_based_roles)

    if current_app.org_manager is not None:
        roles = current_app.org_manager.refresh_roles(db_id)
        db_user['roles'] = list(roles)

    return db_user, status


def validate_token(user_id, token, oauth_subclient_id):
    """Verifies a subclient token with Blender ID.

    :returns: (user info, token expiry) on success, or (None, None) on failure.
        The user information from Blender ID is returned as dict
        {'email': 'a@b', 'full_name': 'AB'}, token expiry as a datime.datetime.
    :rtype: dict
    """

    our_subclient_id = current_app.config['BLENDER_ID_SUBCLIENT_ID']

    # Check that IF there is a subclient ID given, it is the correct one.
    if oauth_subclient_id and our_subclient_id != oauth_subclient_id:
        log.warning('validate_token(): BlenderID user %s is trying to use the wrong subclient '
                    'ID %r; treating as invalid login.', user_id, oauth_subclient_id)
        return None, None

    # Validate against BlenderID.
    log.debug('Validating subclient token for BlenderID user %r, subclient %r', user_id,
              oauth_subclient_id)
    payload = {'user_id': user_id,
               'token': token}
    if oauth_subclient_id:
        # If the subclient ID is set, the token belongs to another OAuth Client,
        # in which case we do not set the client_id field.
        payload['subclient_id'] = oauth_subclient_id
    else:
        # We only want to accept Blender Cloud tokens.
        payload['client_id'] = current_app.config['OAUTH_CREDENTIALS']['blender-id']['id']

    blender_id_endpoint = current_app.config['BLENDER_ID_ENDPOINT']
    url = urljoin(blender_id_endpoint, 'u/validate_token')
    log.debug('POSTing to %r', url)

    # POST to Blender ID, handling errors as negative verification results.
    s = Session()
    try:
        r = s.post(url, data=payload, timeout=5,
                   verify=current_app.config['TLS_CERT_FILE'])
    except requests.exceptions.ConnectionError:
        log.error('Connection error trying to POST to %s, handling as invalid token.', url)
        return None, None
    except requests.exceptions.ReadTimeout:
        log.error('Read timeout trying to POST to %s, handling as invalid token.', url)
        return None, None
    except requests.exceptions.RequestException as ex:
        log.error('Requests error "%s" trying to POST to %s, handling as invalid token.', ex, url)
        return None, None
    except IOError as ex:
        log.error('Unknown I/O error "%s" trying to POST to %s, handling as invalid token.',
                  ex, url)
        return None, None

    if r.status_code != 200:
        log.debug('Token %s invalid, HTTP status %i returned', token, r.status_code)
        return None, None

    resp = r.json()
    if resp['status'] != 'success':
        log.warning('Failed response from %s: %s', url, resp)
        return None, None

    expires = _compute_token_expiry(resp['token_expires'])

    return resp['user'], expires


def _compute_token_expiry(token_expires_string):
    """Computes token expiry based on current time and BlenderID expiry.

    Expires our side of the token when either the BlenderID token expires,
    or in one hour. The latter case is to ensure we periodically verify
    the token.
    """

    # requirement is called python-dateutil, so PyCharm doesn't find it.
    # noinspection PyPackageRequirements
    from dateutil import parser

    blid_expiry = parser.parse(token_expires_string)
    blid_expiry = blid_expiry.astimezone(tz_util.utc)
    our_expiry = utcnow() + datetime.timedelta(hours=1)

    return min(blid_expiry, our_expiry)


def get_user_blenderid(db_user: dict) -> str:
    """Returns the Blender ID user ID for this Pillar user.

    Takes the string from 'auth.*.user_id' for the '*' where 'provider'
    is 'blender-id'.

    :returns the user ID, or the empty string when the user has none.
    """

    bid_user_ids = [auth['user_id']
                    for auth in db_user['auth']
                    if auth['provider'] == 'blender-id']
    try:
        return bid_user_ids[0]
    except IndexError:
        return ''


def fetch_blenderid_user() -> dict:
    """Returns the user info of the currently logged in user from BlenderID.

    Returns an empty dict if communication fails.

    Example dict:
    {
         "email": "some@email.example.com",
         "full_name": "dr. Sybren A. St\u00fcvel",
         "id": 5555,
         "roles": {
           "admin": true,
           "bfct_trainer": false,
           "cloud_has_subscription": true,
           "cloud_subscriber": true,
           "conference_speaker": true,
           "network_member": true
         }
    }

    :raises LogoutUser: when Blender ID tells us the current token is
        invalid, and the user should be logged out.
    """
    import httplib2  # used by the oauth2 package

    my_log = log.getChild('fetch_blenderid_user')

    bid_url = urljoin(current_app.config['BLENDER_ID_ENDPOINT'], 'api/user')
    my_log.debug('Fetching user info from %s', bid_url)

    credentials = current_app.config['OAUTH_CREDENTIALS']['blender-id']
    oauth_token = session.get('blender_id_oauth_token')
    if not oauth_token:
        my_log.warning('no Blender ID oauth token found in user session')
        return {}

    assert isinstance(oauth_token, str), f'oauth token must be str, not {type(oauth_token)}'

    oauth_session = OAuth2Session(
        credentials['id'], credentials['secret'],
        access_token=oauth_token)

    try:
        bid_resp = oauth_session.get(bid_url)
    except httplib2.HttpLib2Error:
        my_log.exception('Error getting %s from BlenderID', bid_url)
        return {}

    if bid_resp.status_code == 403:
        my_log.warning('Error %i from BlenderID %s, logging out user', bid_resp.status_code, bid_url)
        raise LogoutUser()

    if bid_resp.status_code != 200:
        my_log.warning('Error %i from BlenderID %s: %s', bid_resp.status_code, bid_url, bid_resp.text)
        return {}

    payload = bid_resp.json()
    if not payload:
        my_log.warning('Empty data returned from BlenderID %s', bid_url)
        return {}

    my_log.debug('BlenderID returned %s', payload)
    return payload


def avatar_url(blenderid_user_id: str) -> str:
    """Return the URL to the user's avatar on Blender ID.

    This avatar should be downloaded, and not served from the Blender ID URL.
    """
    bid_url = urljoin(current_app.config['BLENDER_ID_ENDPOINT'],
                      f'api/user/{blenderid_user_id}/avatar')
    return bid_url


def setup_app(app, url_prefix):
    app.register_api_blueprint(blender_id, url_prefix=url_prefix)


def switch_user_url(next_url: str) -> str:
    from urllib.parse import quote

    base_url = urljoin(current_app.config['BLENDER_ID_ENDPOINT'], 'switch')
    if next_url:
        return '%s?next=%s' % (base_url, quote(next_url))
    return base_url
