"""Sub-query stuff, for things we would otherwise let Eve embed (but don't want to).

Uses app.cache.memoize() to cache the results. However, since this decorator needs
to run in Flask Application context, it is manually applied in setup_app().
"""

import pillarsdk
import pillarsdk.exceptions
from pillar.web.system_util import pillar_api


def get_user_info(user_id):
    """Returns email, username and full name of the user.

    Only returns the public fields, so the return value is the same
    for authenticated & non-authenticated users, which is why we're
    allowed to cache it globally.

    Returns an empty dict when the user cannot be found.
    """

    if user_id is None:
        return {}

    try:
        user = pillarsdk.User.find(user_id, api=pillar_api())
    except pillarsdk.exceptions.ResourceNotFound:
        return {}

    if not user:
        return {}

    # TODO: put those fields into a config var or module-level global.
    return {'email': user.email,
            'full_name': user.full_name,
            'username': user.username,
            'badges_html': (user.badges and user.badges.html) or ''}


def setup_app(app):
    global get_user_info

    decorator = app.cache.memoize(timeout=300, make_name='%s.get_user_info' % __name__)
    get_user_info = decorator(get_user_info)
