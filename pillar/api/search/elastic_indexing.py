import logging

log = logging.getLogger(__name__)


def push_updated_user(user_to_index: dict):
    """Push an update to the Algolia index when a user item is updated"""

    log.warning(
        'WIP USER ELK INDEXING %s %s',
        user_to_index.get('username'),
        user_to_index.get('objectID'))


def index_node_save(node_to_index: dict):

    log.warning(
        'WIP USER NODE INDEXING %s',
        node_to_index.get('objectID'))


def index_node_delete(delete_id: str):

    log.warning(
        'WIP NODE DELETE INDEXING %s', delete_id)
