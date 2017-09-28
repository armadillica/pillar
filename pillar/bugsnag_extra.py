# Keys in the user's session dictionary that are removed before sending to Bugsnag.
SESSION_KEYS_TO_REMOVE = ('blender_id_oauth_token', 'user_id')


def add_pillar_request_to_notification(notification):
    """Adds request metadata to the Bugsnag notifications.

    This basically copies bugsnag.flask.add_flask_request_to_notification,
    but is altered to include Pillar-specific metadata.
    """
    from flask import request, session
    from bugsnag.wsgi import request_path
    import pillar.auth

    if not request:
        return

    notification.context = "%s %s" % (request.method,
                                      request_path(request.environ))

    if 'id' not in notification.user:
        user: pillar.auth.UserClass = pillar.auth.current_user._get_current_object()
        notification.set_user(id=user.user_id,
                              email=user.email,
                              name=user.username)
        notification.user['roles'] = sorted(user.roles)
        notification.user['capabilities'] = sorted(user.capabilities)

    session_dict = dict(session)
    for key in SESSION_KEYS_TO_REMOVE:
        try:
            del session_dict[key]
        except KeyError:
            pass
    notification.add_tab("session", session_dict)
    notification.add_tab("environment", dict(request.environ))

    remote_addr = request.remote_addr
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        remote_addr = f'{forwarded_for} (proxied via {remote_addr})'

    notification.add_tab("request", {
        "url": request.base_url,
        "headers": dict(request.headers),
        "params": dict(request.form),
        "data": {'request.data': request.data,
                 'request.json': request.get_json()},
        "endpoint": request.endpoint,
        "remote_addr": remote_addr,
    })
