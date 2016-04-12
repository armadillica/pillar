"""Blender ID subclient endpoint."""

import logging
from pprint import pformat

import requests
from flask import Blueprint, request, current_app, abort, jsonify
from eve.methods.post import post_internal
from eve.methods.put import put_internal

from application.utils import authentication, remove_private_keys

blender_id = Blueprint('blender_id', __name__)
log = logging.getLogger(__name__)


@blender_id.route('/store_scst', methods=['POST'])
def store_subclient_token():
    """Verifies & stores a user's subclient-specific token."""

    user_id = request.form['user_id']  # User ID at BlenderID
    scst = request.form['scst']

    # Verify with Blender ID
    log.debug('Storing SCST for BlenderID user %s', user_id)
    user_info = validate_subclient_token(user_id, scst)

    if user_info is None:
        log.warning('Unable to verify subclient token with Blender ID.')
        return jsonify({'status': 'fail',
                        'error': 'BLENDER ID ERROR'}), 403

    # Store the user info in MongoDB.
    log.info('Obtained user info from Blender ID: %s', user_info)
    db_user = find_user_in_db(user_id, scst, **user_info)

    if '_id' in db_user:
        # Update the existing user
        db_id = db_user['_id']
        r, _, _, status = put_internal('users', remove_private_keys(db_user), _id=db_id)
    else:
        # Create a new user
        r, _, _, status = post_internal('users', db_user)
        db_id = r['_id']

    if status not in (200, 201):
        log.error('internal response: %r %r', status, r)
        return abort(500)

    return jsonify({'status': 'success',
                    'subclient_user_id': str(db_id)}), status


def validate_subclient_token(user_id, scst):
    """Verifies a subclient token with Blender ID.

    :returns: the user information from Blender ID on success, in a dict
        {'email': 'a@b', 'full_name': 'AB'}, or None on failure.
    :rtype: dict
    """

    client_id = current_app.config['BLENDER_ID_CLIENT_ID']
    subclient_id = current_app.config['BLENDER_ID_SUBCLIENT_ID']

    log.debug('Validating subclient token for Blender ID user %s', user_id)
    payload = {'client_id': client_id,
               'subclient_id': subclient_id,
               'user_id': user_id,
               'scst': scst}
    url = '{0}/subclients/validate_token'.format(authentication.blender_id_endpoint())
    log.debug('POSTing to %r', url)

    # POST to Blender ID, handling errors as negative verification results.
    try:
        r = requests.post(url, data=payload)
    except requests.exceptions.ConnectionError as e:
        log.error('Connection error trying to POST to %s, handling as invalid token.', url)
        return None

    if r.status_code != 200:
        log.info('Token invalid, HTTP status %i returned', r.status_code)
        return None

    resp = r.json()
    if resp['status'] != 'success':
        log.warning('Failed response from %s: %s', url, resp)
        return None

    return resp['user']


def find_user_in_db(user_id, scst, email, full_name):
    """Find the user in our database, creating/updating it where needed."""

    users = current_app.data.driver.db['users']

    query = {'auth': {'$elemMatch': {'user_id': user_id, 'provider': 'blender-id'}}}
    log.debug('Querying: %s', query)
    db_user = users.find_one(query)

    # TODO: include token expiry in database.
    if db_user:
        log.debug('User %r already in our database, updating with info from Blender ID.', user_id)
        db_user['full_name'] = full_name
        db_user['email'] = email

        auth = next(auth for auth in db_user['auth'] if auth['provider'] == 'blender-id')
        auth['token'] = scst
        return db_user

    log.debug('User %r not yet in our database, create a new one.', user_id)
    db_user = authentication.create_new_user_document(email, user_id, full_name, token=scst)
    db_user['username'] = authentication.make_unique_username(email)
    return db_user
