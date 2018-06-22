"""
Replacement of the old SystemUtility class.
"""

import os
import logging
from flask import current_app, session, request
from flask_login import current_user

from pillar.sdk import FlaskInternalApi

log = logging.getLogger(__name__)


def pillar_server_endpoint():
    """Gets the endpoint for the authentication API. If the env variable
    is defined, we will use the one from the config object.
    """

    return os.environ.get('PILLAR_SERVER_ENDPOINT',
                          current_app.config['PILLAR_SERVER_ENDPOINT'])


def pillar_server_endpoint_static():
    """Endpoint to retrieve static files (previews, videos, etc)"""
    return "{0}/file_server/file/".format(pillar_server_endpoint())


def pillar_api(token=None):
    # Cache API objects on the request per token.
    api = getattr(request, 'pillar_api', {}).get(token)
    if api is not None:
        return api

    # Check if current_user is initialized (in order to support manage.py
    # scripts and non authenticated server requests).
    use_token = token
    if token is None and current_user and current_user.is_authenticated:
        use_token = current_user.id

    api = FlaskInternalApi(
        endpoint=pillar_server_endpoint(),
        username=None,
        password=None,
        token=use_token
    )

    if token is None:
        if not hasattr(request, 'pillar_api'):
            request.pillar_api = {}
        request.pillar_api[token] = api

    return api


def session_item(item):
    return session.get(item, None)
