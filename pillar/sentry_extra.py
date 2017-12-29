from raven.contrib.flask import Sentry

from .auth import current_user
from . import current_app


class PillarSentry(Sentry):
    """Flask Sentry with Pillar support.

    This is mostly for obtaining user information on API calls,
    and for preventing the auth tokens to be logged as user ID.
    """

    def get_user_info(self, request):
        user_info = super().get_user_info(request)

        # The auth token is stored as the user ID in the flask_login
        # current_user object, so don't send that to Sentry.
        user_info.pop('id', None)

        if len(user_info) > 1:
            # Sentry always includes the IP address, but when they find a
            # logged-in user, they add more info. In that case we're done.
            return user_info

        # This is pretty much a copy-paste from Sentry, except that it uses
        # pillar.auth.current_user instead.
        try:
            if not current_user.is_authenticated:
                return user_info
        except AttributeError:
            # HACK: catch the attribute error thrown by flask-login is not attached
            # >   current_user = LocalProxy(lambda: _request_ctx_stack.top.user)
            # E   AttributeError: 'RequestContext' object has no attribute 'user'
            return user_info

        if 'SENTRY_USER_ATTRS' in current_app.config:
            for attr in current_app.config['SENTRY_USER_ATTRS']:
                if hasattr(current_user, attr):
                    user_info[attr] = getattr(current_user, attr)

        return user_info
