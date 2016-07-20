from flask import request
from werkzeug import exceptions as wz_exceptions


def blender_cloud_addon_version():
    """Returns the version of the Blender Cloud Addon, or None if not given in the request.

    Uses the 'Blender-Cloud-Addon' HTTP header.

    :returns: the version of the addon, as tuple (major, minor, micro)
    :rtype: tuple or None
    :raises: werkzeug.exceptions.BadRequest if the header is malformed.
    """

    header = request.headers.get('Blender-Cloud-Addon')
    if not header:
        return None

    parts = header.split('.')
    try:
        return tuple(int(part) for part in parts)
    except ValueError:
        raise wz_exceptions.BadRequest('Invalid Blender-Cloud-Addon header')


def setup_app(app, url_prefix):
    from . import texture_libs, home_project

    texture_libs.setup_app(app, url_prefix=url_prefix)
    home_project.setup_app(app, url_prefix=url_prefix)
