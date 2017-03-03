import base64
import hashlib
import logging
import typing

import bcrypt
import datetime
from bson import tz_util
from flask import abort, Blueprint, current_app, jsonify, request
from pillar.api.utils.authentication import create_new_user_document
from pillar.api.utils.authentication import make_unique_username
from pillar.api.utils.authentication import store_token

blueprint = Blueprint('authentication', __name__)
log = logging.getLogger(__name__)


def get_auth_credentials(user, provider):
    return next((credentials for credentials in user['auth'] if 'provider'
                 in credentials and credentials['provider'] == provider), None)


def create_local_user(email, password):
    """For internal user only. Given username and password, create a user."""
    # Hash the password
    hashed_password = hash_password(password, bcrypt.gensalt())
    db_user = create_new_user_document(email, '', email, provider='local',
                                       token=hashed_password)
    # Make username unique
    db_user['username'] = make_unique_username(email)
    # Create the user
    r, _, _, status = current_app.post_internal('users', db_user)
    if status != 201:
        log.error('internal response: %r %r', status, r)
        return abort(500)
    # Return user ID
    return r['_id']


@blueprint.route('/make-token', methods=['POST'])
def make_token():
    """Direct login for a user, without OAuth, using local database. Generates
    a token that is passed back to Pillar Web and used in subsequent
    transactions.

    :return: a token string
    """
    username = request.form['username']
    password = request.form['password']

    # Look up user in db
    users_collection = current_app.data.driver.db['users']
    user = users_collection.find_one({'username': username})
    if not user:
        return abort(403)
    # Check if user has "local" auth type
    credentials = get_auth_credentials(user, 'local')
    if not credentials:
        return abort(403)
    # Verify password
    salt = credentials['token']
    hashed_password = hash_password(password, salt)
    if hashed_password != credentials['token']:
        return abort(403)

    token = generate_and_store_token(user['_id'])
    return jsonify(token=token['token'])


def generate_and_store_token(user_id, days=15, prefix=b''):
    """Generates token based on random bits.

    :param user_id: ObjectId of the owning user.
    :param days: token will expire in this many days.
    :param prefix: the token will be prefixed by these bytes, for easy identification.
    :return: the token document.
    """

    if not isinstance(prefix, bytes):
        raise TypeError('prefix must be bytes, not %s' % type(prefix))

    import secrets

    random_bits = secrets.token_bytes(32)

    # Use 'xy' as altargs to prevent + and / characters from appearing.
    # We never have to b64decode the string anyway.
    token = prefix + base64.b64encode(random_bits, altchars=b'xy').strip(b'=')

    token_expiry = datetime.datetime.now(tz=tz_util.utc) + datetime.timedelta(days=days)
    return store_token(user_id, token.decode('ascii'), token_expiry)


def hash_password(password: str, salt: typing.Union[str, bytes]) -> str:
    password = password.encode()

    if isinstance(salt, str):
        salt = salt.encode('utf-8')

    hash = hashlib.sha256(password).digest()
    encoded_password = base64.b64encode(hash)
    hashed_password = bcrypt.hashpw(encoded_password, salt)
    return hashed_password.decode('ascii')


def setup_app(app, url_prefix):
    app.register_api_blueprint(blueprint, url_prefix=url_prefix)
