import logging

from algoliasearch.helpers import AlgoliaException
import bson

from pillar import current_app

log = logging.getLogger(__name__)


@current_app.celery.task(ignore_result=True)
def push_updated_user_to_algolia(user_id: str):
    """Push an update to the Algolia index when a user item is updated"""

    from pillar.api.utils.algolia import algolia_index_user_save

    user_oid = bson.ObjectId(user_id)
    log.info('Retrieving user %s', user_oid)
    users_coll = current_app.db('users')
    user = users_coll.find_one({'_id': user_oid})
    if user is None:
        log.warning('Unable to find user %s, not updating Algolia.', user_oid)
        return

    try:
        algolia_index_user_save(user)
    except AlgoliaException as ex:
        log.warning('Unable to push user info to Algolia for user "%s", id=%s; %s',
                    user.get('username'), user_id, ex)


@current_app.celery.task(ignore_result=True)
def algolia_index_node_save(node_id: str):
    from pillar.api.utils.algolia import algolia_index_node_save

    node_oid = bson.ObjectId(node_id)
    log.info('Retrieving node %s', node_oid)

    nodes_coll = current_app.db('nodes')
    node = nodes_coll.find_one({'_id': node_oid})

    if node is None:
        log.warning('Unable to find node %s, not updating Algolia.', node_id)
        return

    try:
        algolia_index_node_save(node)
    except AlgoliaException as ex:
        log.warning('Unable to push node info to Algolia for node %s; %s', node_id, ex)


@current_app.celery.task(ignore_result=True)
def algolia_index_node_delete(node_id: str):
    from pillar.api.utils.algolia import algolia_index_node_delete

    # Deleting a node takes nothing more than the ID anyway. No need to fetch anything from Mongo.
    fake_node = {'_id': bson.ObjectId(node_id)}

    try:
        algolia_index_node_delete(fake_node)
    except AlgoliaException as ex:
        log.warning('Unable to delete node info to Algolia for node %s; %s', node_id, ex)
