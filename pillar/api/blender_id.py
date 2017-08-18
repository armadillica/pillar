"""Blender ID subclient endpoint.

Also contains functionality for other parts of Pillar to perform communication
with Blender ID.
"""

import datetime
import logging

import requests
from bson import tz_util
from rauth import OAuth2Session
from flask import Blueprint, request, current_app, jsonify, session
from requests.adapters import HTTPAdapter

from pillar.api.utils import authentication
from pillar.api.utils.authentication import find_user_in_db, upsert_user

blender_id = Blueprint('blender_id', __name__)
log = logging.getLogger(__name__)


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


def blender_id_endpoint():
    """Gets the endpoint for the authentication API. If the env variable
    is defined, it's possible to override the (default) production address.
    """
    return current_app.config['BLENDER_ID_ENDPOINT'].rstrip('/')


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
    authentication.store_token(db_id, token, token_expiry, oauth_subclient_id)

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
        payload['subclient_id'] = oauth_subclient_id

    url = '{0}/u/validate_token'.format(blender_id_endpoint())
    log.debug('POSTing to %r', url)

    # Retry a few times when POSTing to BlenderID fails.
    # Source: http://stackoverflow.com/a/15431343/875379
    s = requests.Session()
    s.mount(blender_id_endpoint(), HTTPAdapter(max_retries=5))

    # POST to Blender ID, handling errors as negative verification results.
    try:
        r = s.post(url, data=payload, timeout=5,
                   verify=current_app.config['TLS_CERT_FILE'])
    except requests.exceptions.ConnectionError as e:
        log.error('Connection error trying to POST to %s, handling as invalid token.', url)
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
    our_expiry = datetime.datetime.now(tz=tz_util.utc) + datetime.timedelta(hours=1)

    return min(blid_expiry, our_expiry)


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
           "cloud_single_member": true,
           "conference_speaker": true,
           "network_member": true
         }
    }

    """

    import httplib2  # used by the oauth2 package

    bid_url = '%s/api/user' % blender_id_endpoint()
    log.debug('Fetching user info from %s', bid_url)
    try:
        client_id = current_app.config['OAUTH_CREDENTIALS']['blender-id']['id']
        client_secret = current_app.config['OAUTH_CREDENTIALS']['blender-id']['secret']
        oauth_session = OAuth2Session(
            client_id, client_secret, access_token=session['blender_id_oauth_token'])
        bid_resp = oauth_session.get(bid_url)
    except httplib2.HttpLib2Error:
        log.exception('Error getting %s from BlenderID', bid_url)
        return {}

    if bid_resp.status_code != 200:
        log.warning('Error %i from BlenderID %s: %s', bid_resp.status_code, bid_url, bid_resp.data)
        return {}

    if not bid_resp.json():
        log.warning('Empty data returned from BlenderID %s', bid_url)
        return {}

    log.debug('BlenderID returned %s', bid_resp.json())
    return bid_resp.json()


def setup_app(app, url_prefix):
    app.register_api_blueprint(blender_id, url_prefix=url_prefix)


def switch_user_url(next_url: str) -> str:
    from urllib.parse import quote

    base_url = '%s/switch' % blender_id_endpoint()
    if next_url:
        return '%s?next=%s' % (base_url, quote(next_url))
    return base_url
