import os
import logging

import requests

from datetime import datetime
from datetime import timedelta
from flask import g
from flask import request
from eve.methods.post import post_internal

from application import app

log = logging.getLogger(__name__)


class SystemUtility():
    def __new__(cls, *args, **kwargs):
        raise TypeError("Base class may not be instantiated")

    @staticmethod
    def blender_id_endpoint():
        """Gets the endpoint for the authentication API. If the env variable
        is defined, it's possible to override the (default) production address.
        """
        return app.config['BLENDER_ID_ENDPOINT']


def validate(token):
    """Validate a token against the Blender ID server. This simple lookup
    returns a dictionary with the following keys:

    - message: a success message
    - valid: a boolean, stating if the token is valid
    - user: a dictionary with information regarding the user
    """

    log.debug("Validating token %s", token)
    payload = dict(
        token=token)
    try:
        r = requests.post("{0}/u/validate_token".format(
            SystemUtility.blender_id_endpoint()), data=payload)
    except requests.exceptions.ConnectionError as e:
        raise e

    if r.status_code != 200:
        log.info('HTTP error %i validating token: %s', r.status_code, r.content)
        return None

    return r.json()


def validate_token():
    """Validate the token provided in the request and populate the current_user
    flask.g object, so that permissions and access to a resource can be defined
    from it.

    When the token is succesfully validated, sets `g.current_user` to contain
    the user information.

    @returns True iff the user is logged in with a valid Blender ID token.
    """

    if not request.authorization:
        # If no authorization headers are provided, we are getting a request
        # from a non logged in user. Proceed accordingly.
        return False

    token = request.authorization.username
    tokens_collection = app.data.driver.db['tokens']

    lookup = {'token': token, 'expire_time': {"$gt": datetime.now()}}
    db_token = tokens_collection.find_one(lookup)
    if not db_token:
        # If no valid token is found in our local database, we issue a new
        # request to the Blender ID server to verify the validity of the token
        #  passed via the HTTP header. We will get basic user info if the user
        # is authorized, and we will store the token in our local database.
        validation = validate(token)
        if validation is None or validation.get('status', '') != 'success':
            return False

        users = app.data.driver.db['users']
        email = validation['data']['user']['email']
        db_user = users.find_one({'email': email})
        username = make_unique_username(email)

        if not db_user:
            # We don't even know this user; create it on the fly.
            user_id = create_new_user(
                email, username, validation['data']['user']['id'])
            groups = None
        else:
            user_id = db_user['_id']
            groups = db_user['groups']

        token_data = {
            'user': user_id,
            'token': token,
            'expire_time': datetime.now() + timedelta(hours=1)
        }
        post_internal('tokens', token_data)
        current_user = dict(
            user_id=user_id,
            token=token,
            groups=groups,
            token_expire_time=datetime.now() + timedelta(hours=1))
    else:
        users = app.data.driver.db['users']
        db_user = users.find_one(db_token['user'])
        current_user = dict(
            user_id=db_token['user'],
            token=db_token['token'],
            groups=db_user['groups'],
            token_expire_time=db_token['expire_time'])

    g.current_user = current_user

    return True


def create_new_user(email, username, user_id):
    """Creates a new user in our local database.

    @param email: the user's email
    @param username: the username, which is also used as full name.
    @param user_id: the user ID from the Blender ID server.
    @returns: the user ID from our local database.
    """

    user_data = {
        'full_name': username,
        'username': username,
        'email': email,
        'auth': [{
            'provider': 'blender-id',
            'user_id': str(user_id),
            'token': ''}],
        'settings': {
            'email_communications': 1
        }
    }
    r = post_internal('users', user_data)
    user_id = r[0]['_id']
    return user_id


def make_unique_username(email):
    """Creates a unique username from the email address.

    @param email: the email address
    @returns: the new username
    @rtype: str
    """

    username = email.split('@')[0]
    # Check for min length of username (otherwise validation fails)
    username = "___{0}".format(username) if len(username) < 3 else username

    users = app.data.driver.db['users']
    user_from_username = users.find_one({'username': username})

    if not user_from_username:
        return username

    # Username exists, make it unique by adding some number after it.
    suffix = 1
    while True:
        unique_name = '%s%i' % (username, suffix)
        user_from_username = users.find_one({'username': unique_name})
        if user_from_username is None:
            return unique_name
        suffix += 1
