"""Authentication code common to the web and api modules."""

import logging

from flask import current_app, session
import flask_login
import flask_oauthlib.client

from ..api import utils, blender_id
from ..api.utils import authentication

log = logging.getLogger(__name__)


class UserClass(flask_login.UserMixin):
    def __init__(self, token):
        # We store the Token instead of ID
        self.id = token
        self.username = None
        self.full_name = None
        self.objectid = None
        self.gravatar = None
        self.email = None
        self.roles = []

    def has_role(self, *roles):
        """Returns True iff the user has one or more of the given roles."""

        if not self.roles:
            return False

        return bool(set(self.roles).intersection(set(roles)))


class AnonymousUser(flask_login.AnonymousUserMixin):
    @property
    def objectid(self):
        """Anonymous user has no settable objectid."""
        return None

    def has_role(self, *roles):
        return False


def _load_user(token):
    """Loads a user by their token.

    :returns: returns a UserClass instance if logged in, or an AnonymousUser() if not.
    :rtype: UserClass
    """

    db_user = authentication.validate_this_token(token)
    if not db_user:
        return AnonymousUser()

    login_user = UserClass(token)
    login_user.email = db_user['email']
    login_user.objectid = unicode(db_user['_id'])
    login_user.username = db_user['username']
    login_user.gravatar = utils.gravatar(db_user['email'])
    login_user.roles = db_user.get('roles', [])
    login_user.groups = [unicode(g) for g in db_user['groups'] or ()]
    login_user.full_name = db_user.get('full_name', '')

    return login_user


def config_login_manager(app):
    """Configures the Flask-Login manager, used for the web endpoints."""

    login_manager = flask_login.LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "users.login"
    login_manager.anonymous_user = AnonymousUser
    # noinspection PyTypeChecker
    login_manager.user_loader(_load_user)

    return login_manager


def login_user(oauth_token):
    """Log in the user identified by the given token."""

    user = UserClass(oauth_token)
    flask_login.login_user(user)


def get_blender_id_oauth_token():
    """Returns a tuple (token, ''), for use with flask_oauthlib."""
    return session.get('blender_id_oauth_token')


def config_oauth_login(app):
    config = app.config
    if not config.get('SOCIAL_BLENDER_ID'):
        log.info('OAuth Blender-ID login not setup.')
        return None

    oauth = flask_oauthlib.client.OAuth(app)
    social_blender_id = config.get('SOCIAL_BLENDER_ID')

    oauth_blender_id = oauth.remote_app(
        'blender_id',
        consumer_key=social_blender_id['app_id'],
        consumer_secret=social_blender_id['app_secret'],
        request_token_params={'scope': 'email'},
        base_url=config['BLENDER_ID_OAUTH_URL'],
        request_token_url=None,
        access_token_url=config['BLENDER_ID_BASE_ACCESS_TOKEN_URL'],
        authorize_url=config['BLENDER_ID_AUTHORIZE_URL']
    )

    oauth_blender_id.tokengetter(get_blender_id_oauth_token)
    log.info('OAuth Blender-ID login setup as %s', social_blender_id['app_id'])

    return oauth_blender_id
