"""
Replacement of the old SystemUtility class.
"""

import os
import logging
from flask import current_app, session
from flask_login import current_user

from pillar.sdk import FlaskInternalApi

log = logging.getLogger(__name__)


def blender_id_endpoint():
    """Gets the endpoint for the authentication API. If the env variable
    is defined, it's possible to override the (default) production address.
    """
    return os.environ.get('BLENDER_ID_ENDPOINT',
                          "https://www.blender.org/id").rstrip('/')


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
    # Check if current_user is initialized (in order to support manage.py
    # scripts and non authenticated server requests).
    if token is None and current_user and current_user.is_authenticated:
        token = current_user.id

    api = FlaskInternalApi(
        endpoint=pillar_server_endpoint(),
        username=None,
        password=None,
        token=token
    )

    return api


def session_item(item):
    return session.get(item, None)
