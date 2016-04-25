import hashlib
import json
import logging
import urllib

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


def setup_app(app):
    app.on_post_GET_users += post_GET_user
    app.on_replace_users += after_replacing_user
