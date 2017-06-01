import logging

import bson

from pillar import current_app

log = logging.getLogger(__name__)


@current_app.celery.task(ignore_result=True)
def push_updated_user_to_algolia(user_id: str):
    """Push an update to the Algolia index when a user item is updated"""

    from algoliasearch.helpers import AlgoliaException
    from pillar.api.utils.algolia import algolia_index_user_save

    user_oid = bson.ObjectId(user_id)
    log.info('Retrieving user %s', user_oid)
    users_coll = current_app.db('users')
    user = users_coll.find_one({'_id': user_oid})

    try:
        algolia_index_user_save(user)
    except AlgoliaException as ex:
        log.warning('Unable to push user info to Algolia for user "%s", id=%s; %s',
                    user.get('username'), user.get('_id'), ex)
