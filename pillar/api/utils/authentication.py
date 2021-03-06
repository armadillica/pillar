"""Generic authentication.

Contains functionality to validate tokens, create users and tokens, and make
unique usernames from emails. Calls out to the pillar_server.modules.blender_id
module for Blender ID communication.
"""

import base64
import datetime
import hmac
import hashlib
import logging
import typing

import bson
from flask import g, current_app, session
from flask import request
from werkzeug import exceptions as wz_exceptions

from pillar.api.utils import remove_private_keys, utcnow

log = logging.getLogger(__name__)

# Construction is done when requested, since constructing a UserClass instance
# requires an application context to look up capabilities. We set the initial
# value to a not-None singleton to be able to differentiate between
# g.current_user set to "not logged in" or "uninitialised CLI_USER".
CLI_USER = ...


def force_cli_user():
    """Sets g.current_user to the CLI_USER object.

    This is used as a marker to avoid authorization checks and just allow everything.
    """

    global CLI_USER

    from pillar.auth import UserClass

    if CLI_USER is ...:
        CLI_USER = UserClass.construct('CLI', {
            '_id': 'CLI',
            'groups': [],
            'roles': {'admin'},
            'email': 'local@nowhere',
            'username': 'CLI',
        })
        log.info('CONSTRUCTED CLI USER %s of type %s', id(CLI_USER), id(type(CLI_USER)))

    log.info('Logging in as CLI_USER (%s) of type %s, circumventing authentication.',
             id(CLI_USER), id(type(CLI_USER)))
    g.current_user = CLI_USER


def find_user_in_db(user_info: dict, provider='blender-id') -> dict:
    """Find the user in our database, creating/updating the returned document where needed.

    First, search for the user using its id from the provider, then try to look the user up via the
    email address.

    Does NOT update the user in the database.
    
    :param user_info: Information (id, email and full_name) from the auth provider
    :param provider: One of the supported providers
    """

    users = current_app.data.driver.db['users']

    user_id = user_info['id']
    query = {'$or': [
        {'auth': {'$elemMatch': {
            'user_id': str(user_id),
            'provider': provider}}},
        {'email': user_info['email']},
    ]}
    log.debug('Querying: %s', query)
    db_user = users.find_one(query)

    if db_user:
        log.debug('User with %s id %s already in our database, updating with info from %s',
                  provider, user_id, provider)
        db_user['email'] = user_info['email']

        # Find out if an auth entry for the current provider already exists
        provider_entry = [element for element in db_user['auth'] if element['provider'] == provider]
        if not provider_entry:
            db_user['auth'].append({
                'provider': provider,
                'user_id': str(user_id),
                'token': ''})
    else:
        log.debug('User %r not yet in our database, create a new one.', user_id)
        db_user = create_new_user_document(
            email=user_info['email'],
            user_id=user_id,
            username=user_info['full_name'],
            provider=provider)
        db_user['username'] = make_unique_username(user_info['email'])
        if not db_user['full_name']:
            db_user['full_name'] = db_user['username']

    return db_user


def validate_token(*, force=False) -> bool:
    """Validate the token provided in the request and populate the current_user
    flask.g object, so that permissions and access to a resource can be defined
    from it.

    When the token is successfully validated, sets `g.current_user` to contain
    the user information, otherwise it is set to None.

    :param force: don't trust g.current_user and force a re-check.
    :returns: True iff the user is logged in with a valid Blender ID token.
    """

    import pillar.auth

    # Trust a pre-existing g.current_user
    if not force:
        cur = getattr(g, 'current_user', None)
        if cur is not None and cur.is_authenticated:
            log.debug('skipping token check because current user is already set to %s', cur)
            return True

    auth_header = request.headers.get('Authorization') or ''
    if request.authorization:
        token = request.authorization.username
        oauth_subclient = request.authorization.password
    elif auth_header.startswith('Bearer '):
        token = auth_header[7:].strip()
        oauth_subclient = ''
    else:
        # Check the session, the user might be logged in through Flask-Login.

        # The user has a logged-in session; trust only if this request passes a CSRF check.
        # FIXME(Sybren): we should stop saving the token as 'user_id' in the sesion.
        token = session.get('user_id')
        if token:
            log.debug('skipping token check because current user already has a session')
            current_app.csrf.protect()
        else:
            token = pillar.auth.get_blender_id_oauth_token()
        oauth_subclient = None

    if not token:
        # If no authorization headers are provided, we are getting a request
        # from a non logged in user. Proceed accordingly.
        log.debug('No authentication headers, so not logged in.')
        g.current_user = pillar.auth.AnonymousUser()
        return False

    return validate_this_token(token, oauth_subclient) is not None


def validate_this_token(token, oauth_subclient=None):
    """Validates a given token, and sets g.current_user.

    :returns: the user in MongoDB, or None if not a valid token.
    :rtype: dict
    """

    from pillar.auth import UserClass, AnonymousUser, user_authenticated

    g.current_user = None
    _delete_expired_tokens()

    # Check the users to see if there is one with this Blender ID token.
    db_token = find_token(token, oauth_subclient)
    if not db_token:
        log.debug('Token %r not found in our local database.', token)

        # If no valid token is found in our local database, we issue a new
        # request to the Blender ID server to verify the validity of the token
        # passed via the HTTP header. We will get basic user info if the user
        # is authorized, and we will store the token in our local database.
        from pillar.api import blender_id

        db_user, status = blender_id.validate_create_user('', token, oauth_subclient)
    else:
        # log.debug("User is already in our database and token hasn't expired yet.")
        users = current_app.data.driver.db['users']
        db_user = users.find_one(db_token['user'])

    if db_user is None:
        log.debug('Validation failed, user not logged in')
        g.current_user = AnonymousUser()
        return None

    g.current_user = UserClass.construct(token, db_user)
    user_authenticated.send(g.current_user)

    return db_user


def remove_token(token: str):
    """Removes the token from the database."""

    tokens_coll = current_app.db('tokens')
    token_hashed = hash_auth_token(token)

    # TODO: remove matching on hashed tokens once all hashed tokens have expired.
    lookup = {'$or': [{'token': token}, {'token_hashed': token_hashed}]}
    del_res = tokens_coll.delete_many(lookup)
    log.debug('Removed token %r, matched %d documents', token, del_res.deleted_count)


def find_token(token, is_subclient_token=False, **extra_filters):
    """Returns the token document, or None if it doesn't exist (or is expired)."""

    tokens_coll = current_app.db('tokens')
    token_hashed = hash_auth_token(token)

    # TODO: remove matching on hashed tokens once all hashed tokens have expired.
    lookup = {'$or': [{'token': token}, {'token_hashed': token_hashed}],
              'is_subclient_token': True if is_subclient_token else {'$in': [False, None]},
              'expire_time': {"$gt": utcnow()}}
    lookup.update(extra_filters)

    db_token = tokens_coll.find_one(lookup)
    return db_token


def hash_auth_token(token: str) -> str:
    """Returns the hashed authentication token.

    The token is hashed using HMAC and then base64-encoded.
    """

    hmac_key = current_app.config['AUTH_TOKEN_HMAC_KEY']
    token_hmac = hmac.new(hmac_key, msg=token.encode('utf8'), digestmod=hashlib.sha256)
    digest = token_hmac.digest()

    return base64.b64encode(digest).decode('ascii')


def store_token(user_id,
                token: str,
                token_expiry,
                oauth_subclient_id=False,
                *,
                org_roles: typing.Set[str] = frozenset(),
                oauth_scopes: typing.Optional[typing.List[str]] = None,
                ):
    """Stores an authentication token.

    :returns: the token document from MongoDB
    """

    assert isinstance(token, str), 'token must be string type, not %r' % type(token)

    token_data = {
        'user': user_id,
        'token': token,
        'expire_time': token_expiry,
    }
    if oauth_subclient_id:
        token_data['is_subclient_token'] = True
    if org_roles:
        token_data['org_roles'] = sorted(org_roles)
    if oauth_scopes:
        token_data['oauth_scopes'] = oauth_scopes

    r, _, _, status = current_app.post_internal('tokens', token_data)

    if status not in {200, 201}:
        log.error('Unable to store authentication token: %s', r)
        raise RuntimeError('Unable to store authentication token.')

    token_data.update(r)
    return token_data


def create_new_user(email, username, user_id):
    """Creates a new user in our local database.

    @param email: the user's email
    @param username: the username, which is also used as full name.
    @param user_id: the user ID from the Blender ID server.
    @returns: the user ID from our local database.
    """

    user_data = create_new_user_document(email, user_id, username)
    r = current_app.post_internal('users', user_data)
    user_id = r[0]['_id']
    return user_id


def create_new_user_document(email, user_id, username, provider='blender-id',
                             token='', *, full_name=''):
    """Creates a new user document, without storing it in MongoDB. The token
    parameter is a password in case provider is "local".
    """

    user_data = {
        'full_name': full_name or username,
        'username': username,
        'email': email,
        'auth': [{
            'provider': provider,
            'user_id': str(user_id),
            'token': token}],
        'settings': {
            'email_communications': 1
        },
        'groups': [],
    }
    return user_data


def make_unique_username(email):
    """Creates a unique username from the email address.

    @param email: the email address
    @returns: the new username
    @rtype: str
    """

    username = email.split('@')[0]
    # Check for min length of username (otherwise validation fails)
    username = "___{0}".format(username) if len(username) < 3 else username

    users = current_app.data.driver.db['users']
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


def _delete_expired_tokens():
    """Deletes tokens that have expired.

    For debugging, we keep expired tokens around for a few days, so that we
    can determine that a token was expired rather than not created in the
    first place. It also grants some leeway in clock synchronisation.
    """

    token_coll = current_app.data.driver.db['tokens']

    expiry_date = utcnow() - datetime.timedelta(days=7)
    result = token_coll.delete_many({'expire_time': {"$lt": expiry_date}})
    # log.debug('Deleted %i expired authentication tokens', result.deleted_count)


def current_user_id() -> typing.Optional[bson.ObjectId]:
    """None-safe fetching of user ID. Can return None itself, though."""

    user = current_user()
    return user.user_id


def current_user():
    """Returns the current user, or an AnonymousUser if not logged in.

    :rtype: pillar.auth.UserClass
    """

    import pillar.auth

    user: pillar.auth.UserClass = g.get('current_user')
    if user is None:
        return pillar.auth.AnonymousUser()

    return user


def setup_app(app):
    @app.before_request
    def validate_token_at_each_request():
        validate_token()


def upsert_user(db_user):
    """Inserts/updates the user in MongoDB.

    Retries a few times when there are uniqueness issues in the username.

    :returns: the user's database ID and the status of the PUT/POST.
        The status is 201 on insert, and 200 on update.
    :type: (ObjectId, int)
    """

    if 'subscriber' in db_user.get('groups', []):
        log.error('Non-ObjectID string found in user.groups: %s', db_user)
        raise wz_exceptions.InternalServerError(
            'Non-ObjectID string found in user.groups: %s' % db_user)

    if not db_user['full_name']:
        # Blender ID doesn't need a full name, but we do.
        db_user['full_name'] = db_user['username']

    r = {}
    for retry in range(5):
        if '_id' in db_user:
            # Update the existing user
            attempted_eve_method = 'PUT'
            db_id = db_user['_id']
            r, _, _, status = current_app.put_internal('users', remove_private_keys(db_user),
                                                       _id=db_id)
            if status == 422:
                log.error('Status %i trying to PUT user %s with values %s, should not happen! %s',
                          status, db_id, remove_private_keys(db_user), r)
        else:
            # Create a new user, retry for non-unique usernames.
            attempted_eve_method = 'POST'
            r, _, _, status = current_app.post_internal('users', db_user)

            if status not in {200, 201}:
                log.error('Status %i trying to create user with values %s: %s',
                          status, db_user, r)
                raise wz_exceptions.InternalServerError()

            db_id = r['_id']
            db_user.update(r)  # update with database/eve-generated fields.

        if status == 422:
            # Probably non-unique username, so retry a few times with different usernames.
            log.info('Error creating new user: %s', r)
            username_issue = r.get('_issues', {}).get('username', '')
            if 'not unique' in username_issue:
                # Retry
                db_user['username'] = make_unique_username(db_user['email'])
                continue

        # Saving was successful, or at least didn't break on a non-unique username.
        break
    else:
        log.error('Unable to create new user %s: %s', db_user, r)
        raise wz_exceptions.InternalServerError()

    if status not in (200, 201):
        log.error('internal response from %s to Eve: %r %r', attempted_eve_method, status, r)
        raise wz_exceptions.InternalServerError()

    return db_id, status
