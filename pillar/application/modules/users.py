import hashlib
import json
import logging
import urllib

from flask import g
from eve.auth import TokenAuth
from werkzeug.exceptions import Forbidden

from application.utils.authorization import user_has_role

log = logging.getLogger(__name__)


def gravatar(email, size=64):
    parameters = {'s': str(size), 'd': 'mm'}
    return "https://www.gravatar.com/avatar/" + \
           hashlib.md5(str(email)).hexdigest() + \
           "?" + urllib.urlencode(parameters)


def post_GET_user(request, payload):
    json_data = json.loads(payload.data)
    # Check if we are querying the users endpoint (instead of the single user)
    if json_data.get('_id') is None:
        return
    # json_data['computed_permissions'] = \
    #     compute_permissions(json_data['_id'], app.data.driver)
    payload.data = json.dumps(json_data)


def after_replacing_user(item, original):
    """Push an update to the Algolia index when a user item is updated"""

    from algoliasearch.client import AlgoliaException
    from application.utils.algolia import algolia_index_user_save

    try:
        algolia_index_user_save(item)
    except AlgoliaException as ex:
        log.warning('Unable to push user info to Algolia for user "%s", id=%s; %s',
                    item.get('username'), item.get('_id'), ex)


def before_getting_users(request, lookup):
    """Modifies the lookup dict to limit returned user info."""

    # No access when not logged in.
    current_user = g.get('current_user')
    if current_user is None:
        raise Forbidden()

    # Admins can do anything and get everything, except the 'auth' block.
    if user_has_role(u'admin'):
        return

    # Only allow access to the current user.
    if '_id' in lookup:
        if str(lookup['_id']) != str(current_user['user_id']):
            raise Forbidden()
        return

    # Add a filter to only return the current user.
    lookup['_id'] = current_user['user_id']


def after_fetching_user(user):
    # Deny access to auth block; authentication stuff is managed by
    # custom end-points.
    user.pop('auth', None)


def after_fetching_user_resource(response):
    for user in response['_items']:
        after_fetching_user(user)


def setup_app(app):
    app.on_pre_GET_users += before_getting_users
    app.on_post_GET_users += post_GET_user
    app.on_replace_users += after_replacing_user
    app.on_fetched_item_users += after_fetching_user
    app.on_fetched_resource_users += after_fetching_user_resource
