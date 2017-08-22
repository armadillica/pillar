"""Authentication code common to the web and api modules."""

import collections
import logging
import typing

from flask import session
import flask_login
import flask_oauthlib.client
from werkzeug.local import LocalProxy

from pillar import current_app

import bson

from ..api import utils
from ..api.utils import authentication

log = logging.getLogger(__name__)

# Mapping from user role to capabilities obtained by users with that role.
CAPABILITIES = collections.defaultdict(**{
    'subscriber': {'subscriber', 'home-project'},
    'demo': {'subscriber', 'home-project'},
    'admin': {'subscriber', 'home-project', 'video-encoding', 'admin',
              'view-pending-nodes', 'edit-project-node-types'},
}, default_factory=frozenset)


class UserClass(flask_login.UserMixin):
    def __init__(self, token: typing.Optional[str]):
        # We store the Token instead of ID
        self.id = token
        self.username: str = None
        self.full_name: str = None
        self.user_id: bson.ObjectId = None
        self.objectid: str = None
        self.gravatar: str = None
        self.email: str = None
        self.roles: typing.List[str] = []
        self.groups: typing.List[str] = []  # NOTE: these are stringified object IDs.
        self.group_ids: typing.List[bson.ObjectId] = []
        self.capabilities: typing.Set[str] = set()

    @classmethod
    def construct(cls, token: str, db_user: dict) -> 'UserClass':
        """Constructs a new UserClass instance from a Mongo user document."""

        user = UserClass(token)

        user.user_id = db_user['_id']
        user.roles = db_user.get('roles') or []
        user.group_ids = db_user.get('groups') or []
        user.email = db_user.get('email') or ''
        user.username = db_user['username']
        user.full_name = db_user.get('full_name') or ''

        # Derived properties
        user.objectid = str(db_user['_id'])
        user.gravatar = utils.gravatar(user.email)
        user.groups = [str(g) for g in user.group_ids]
        user.collect_capabilities()

        return user

    def __str__(self):
        return f'UserClass(user_id={self.user_id})'

    def __getitem__(self, item):
        """Compatibility layer with old dict-based g.current_user object."""

        if item == 'user_id':
            return self.user_id
        if item == 'groups':
            return self.group_ids
        if item == 'roles':
            return set(self.roles)

        raise KeyError(f'No such key {item!r}')

    def get(self, key, default=None):
        """Compatibility layer with old dict-based g.current_user object."""

        try:
            return self[key]
        except KeyError:
            return default

    def collect_capabilities(self):
        """Constructs the capabilities set given the user's current roles.

        Requires an application context to be active.
        """

        app_caps = current_app.user_caps

        self.capabilities = set().union(*(app_caps[role] for role in self.roles))

    def has_role(self, *roles):
        """Returns True iff the user has one or more of the given roles."""

        if not self.roles:
            return False

        return bool(set(self.roles).intersection(set(roles)))

    def has_cap(self, *capabilities: typing.Iterable[str]) -> bool:
        """Returns True iff the user has one or more of the given capabilities."""

        if not self.capabilities:
            return False

        return bool(set(self.capabilities).intersection(set(capabilities)))

    def matches_roles(self,
                      require_roles=set(),
                      require_all=False) -> bool:
        """Returns True iff the user's roles matches the query.

        :param require_roles: set of roles.
        :param require_all:
            When False (the default): if the user's roles have a
            non-empty intersection with the given roles, returns True.
            When True: require the user to have all given roles before
            returning True.
        """

        if not isinstance(require_roles, set):
            raise TypeError(f'require_roles param should be a set, but is {type(require_roles)!r}')

        if require_all and not require_roles:
            raise ValueError('require_login(require_all=True) cannot be used with '
                             'empty require_roles.')

        intersection = require_roles.intersection(self.roles)
        if require_all:
            return len(intersection) == len(require_roles)

        return not bool(require_roles) or bool(intersection)


class AnonymousUser(flask_login.AnonymousUserMixin, UserClass):
    def __init__(self):
        super().__init__(token=None)

    def has_role(self, *roles):
        return False

    def has_cap(self, *capabilities):
        return False


def _load_user(token) -> typing.Union[UserClass, AnonymousUser]:
    """Loads a user by their token.

    :returns: returns a UserClass instance if logged in, or an AnonymousUser() if not.
    """

    db_user = authentication.validate_this_token(token)
    if not db_user:
        return AnonymousUser()

    user = UserClass.construct(token, db_user)

    return user


def config_login_manager(app):
    """Configures the Flask-Login manager, used for the web endpoints."""

    login_manager = flask_login.LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "users.login"
    login_manager.login_message = ''
    login_manager.anonymous_user = AnonymousUser
    # noinspection PyTypeChecker
    login_manager.user_loader(_load_user)

    return login_manager


def login_user(oauth_token: str, *, load_from_db=False):
    """Log in the user identified by the given token."""

    from flask import g

    if load_from_db:
        user = _load_user(oauth_token)
    else:
        user = UserClass(oauth_token)
    flask_login.login_user(user)
    g.current_user = user


def get_blender_id_oauth_token():
    """Returns a tuple (token, ''), for use with flask_oauthlib."""

    from flask import request

    token = session.get('blender_id_oauth_token')
    if token:
        return token

    if request.authorization:
        return request.authorization.username, ''

    return None


def config_oauth_login(app):
    config = app.config
    if not config.get('SOCIAL_BLENDER_ID'):
        log.info('OAuth Blender-ID login not set up, no app config SOCIAL_BLENDER_ID.')
        return None
    if not config.get('BLENDER_ID_OAUTH_URL'):
        log.error('Unable to use Blender ID, missing configuration BLENDER_ID_OAUTH_URL.')
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


def _get_current_web_user() -> UserClass:
    """Returns the current web user as a UserClass instance."""

    return flask_login.current_user


current_web_user: UserClass = LocalProxy(_get_current_web_user)
"""The current web user."""
