import logging

from algoliasearch.helpers import AlgoliaException

log = logging.getLogger(__name__)


def push_updated_user(user_to_index: dict):
    """Push an update to the index when a user document is updated."""

    from pillar.api.utils.algolia import index_user_save

    try:
        index_user_save(user_to_index)
    except AlgoliaException as ex:
        log.warning(
            'Unable to push user info to Algolia for user "%s", id=%s; %s',  # noqa
            user_to_index.get('username'),
            user_to_index.get('objectID'), ex)


def index_node_save(node_to_index: dict):
    """Save parsed node document to the index."""
    from pillar.api.utils import algolia

    try:
        algolia.index_node_save(node_to_index)
    except AlgoliaException as ex:
        log.warning(
            'Unable to push node info to Algolia for node %s; %s', node_to_index, ex)  # noqa


def index_node_delete(delete_id: str):
    """Delete node using id."""
    from pillar.api.utils import algolia

    try:
        algolia.index_node_delete(delete_id)
    except AlgoliaException as ex:
        log.warning('Unable to delete node info to Algolia for node %s; %s', delete_id, ex)  # noqa
