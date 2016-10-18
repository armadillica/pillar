"""Sub-query stuff, for things we would otherwise let Eve embed (but don't want to).

Uses app.cache.memoize() to cache the results. However, since this decorator needs
to run in Flask Application context, it is manually applied in setup_app().
"""

import pillarsdk
from pillar.web.system_util import pillar_api


def get_user_info(user_id):
    """Returns email & full name of the user.

    Only returns those two fields, so the return value is the same
    for authenticated & non-authenticated users, which is why we're
    allowed to cache it globally.

    Returns an empty dict when the user cannot be found.
    """

    if user_id is None:
        return {}

    user = pillarsdk.User.find(user_id, api=pillar_api())
    if not user:
        return {}

    return {'email': user.email,
            'full_name': user.full_name}


def setup_app(app):
    global get_user_info

    decorator = app.cache.memoize(timeout=300, make_name='%s.get_user_info' % __name__)
    get_user_info = decorator(get_user_info)
