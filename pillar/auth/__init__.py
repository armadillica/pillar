"""Authentication code common to the web and api modules."""

import collections
import contextlib
import copy
import functools
import logging
import typing

import blinker
from bson import ObjectId
from flask import session, g
import flask_login
from werkzeug.local import LocalProxy

from pillar import current_app

# The sender is the user that was just authenticated.
user_authenticated = blinker.Signal('Sent whenever a user was authenticated')
user_logged_in = blinker.Signal('Sent whenever a user logged in on the web')

log = logging.getLogger(__name__)

# Mapping from user role to capabilities obtained by users with that role.
CAPABILITIES = collections.defaultdict(**{
    'subscriber': {'subscriber', 'home-project'},
    'demo': {'subscriber', 'home-project'},
    'admin': {'video-encoding', 'admin',
              'view-pending-nodes', 'edit-project-node-types'},
}, default_factory=frozenset)


class UserClass(flask_login.UserMixin):
    def __init__(self, token: typing.Optional[str]):
        # We store the Token instead of ID
        self.id = token
        self.auth_token = token
        self.username: str = None
        self.full_name: str = None
        self.user_id: ObjectId = None
        self.objectid: str = None
        self.email: str = None
        self.roles: typing.List[str] = []
        self.groups: typing.List[str] = []  # NOTE: these are stringified object IDs.
        self.group_ids: typing.List[ObjectId] = []
        self.capabilities: typing.Set[str] = set()
        self.nodes: dict = {}  # see the 'nodes' key in eve_settings.py::user_schema.
        self.badges_html: str = ''

        # Stored when constructing a user from the database
        self._db_user = {}

        # Lazily evaluated
        self._has_organizations: typing.Optional[bool] = None

    @classmethod
    def construct(cls, token: str, db_user: dict) -> 'UserClass':
        """Constructs a new UserClass instance from a Mongo user document."""

        user = cls(token)

        user._db_user = copy.deepcopy(db_user)
        user.user_id = db_user.get('_id')
        user.roles = db_user.get('roles') or []
        user.group_ids = db_user.get('groups') or []
        user.email = db_user.get('email') or ''
        user.username = db_user.get('username') or ''
        user.full_name = db_user.get('full_name') or ''
        user.badges_html = db_user.get('badges', {}).get('html') or ''

        # Be a little more specific than just db_user['nodes'] or db_user['avatar']
        user.nodes = {
            'view_progress': db_user.get('nodes', {}).get('view_progress', {}),
        }

        # Derived properties
        user.objectid = str(user.user_id or '')
        user.groups = [str(g) for g in user.group_ids]
        user.collect_capabilities()

        return user

    def __repr__(self):
        return f'UserClass(user_id={self.user_id})'

    def __str__(self):
        return f'{self.__class__.__name__}(id={self.user_id}, email={self.email!r}'

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

    def has_organizations(self) -> bool:
        """Returns True iff this user administers or is member of any organization."""

        if self._has_organizations is None:
            assert self.user_id
            self._has_organizations = current_app.org_manager.user_has_organizations(self.user_id)

        return bool(self._has_organizations)

    def frontend_info(self) -> dict:
        """Return a dictionary of user info for injecting into the page."""

        return {
            'user_id': str(self.user_id),
            'username': self.username,
            'full_name': self.full_name,
            'avatar_url': self.avatar_url,
            'email': self.email,
            'capabilities': list(self.capabilities),
            'badges_html': self.badges_html,
            'is_authenticated': self.is_authenticated,
        }

    @property
    @functools.lru_cache(maxsize=1)
    def avatar_url(self) -> str:
        """Return the Avatar image URL for this user.

        :return: The avatar URL (the default one if the user has no avatar).
        """

        import pillar.api.users.avatar
        return pillar.api.users.avatar.url(self._db_user)


class AnonymousUser(flask_login.AnonymousUserMixin, UserClass):
    def __init__(self):
        super().__init__(token=None)

    def has_role(self, *roles):
        return False

    def has_cap(self, *capabilities):
        return False

    def has_organizations(self) -> bool:
        return False


def _load_user(token) -> typing.Union[UserClass, AnonymousUser]:
    """Loads a user by their token.

    :returns: returns a UserClass instance if logged in, or an AnonymousUser() if not.
    """

    from ..api.utils import authentication

    if not token:
        return AnonymousUser()

    db_user = authentication.validate_this_token(token)
    if not db_user:
        # There is a token, but it's not valid. We should reset the user's session.
        session.clear()
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

    if load_from_db:
        user = _load_user(oauth_token)
    else:
        user = UserClass(oauth_token)
    login_user_object(user)


def login_user_object(user: UserClass):
    """Log in the given user."""
    flask_login.login_user(user, remember=True)
    g.current_user = user
    user_authenticated.send(user)
    user_logged_in.send(user)


def logout_user():
    """Forces a logout of the current user."""

    from ..api.utils import authentication

    token = get_blender_id_oauth_token()
    if token:
        authentication.remove_token(token)

    session.clear()
    flask_login.logout_user()
    g.current_user = AnonymousUser()


@contextlib.contextmanager
def temporary_user(db_user: dict):
    """Temporarily sets the given user as 'current user'.

    Does not trigger login signals, as this is not a real login action.
    """
    try:
        actual_current_user = g.current_user
    except AttributeError:
        actual_current_user = AnonymousUser()

    temp_user = UserClass.construct('', db_user)
    try:
        g.current_user = temp_user
        yield
    finally:
        g.current_user = actual_current_user


def get_blender_id_oauth_token() -> str:
    """Returns the Blender ID auth token, or an empty string if there is none."""

    from flask import request

    token = session.get('blender_id_oauth_token')
    if token:
        if isinstance(token, (tuple, list)):
            # In a past version of Pillar we accidentally stored tuples in the session.
            # Such sessions should be actively fixed.
            # TODO(anyone, after 2017-12-01): refactor this if-block so that it just converts
            # the token value to a string and use that instead.
            token = token[0]
            session['blender_id_oauth_token'] = token
        return token

    if request.authorization and request.authorization.username:
        return request.authorization.username

    if current_user.is_authenticated and current_user.id:
        return current_user.id

    return ''


def get_current_user() -> UserClass:
    """Returns the current user as a UserClass instance.

    Never returns None; returns an AnonymousUser() instance instead.

    This function is intended to be used when pillar.auth.current_user is
    accessed many times in the same scope. Calling this function is then
    more efficient, since it doesn't have to resolve the LocalProxy for
    each access to the returned object.
    """

    from ..api.utils.authentication import current_user

    return current_user()


current_user: UserClass = LocalProxy(get_current_user)
"""The current user."""
