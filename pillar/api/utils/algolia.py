import logging

from bson import ObjectId

from pillar import current_app
from . import skip_when_testing

log = logging.getLogger(__name__)


@skip_when_testing
def index_user_save(to_index_user: dict):
    index_users = current_app.algolia_index_users
    if not index_users:
        log.debug('No Algolia index defined, so nothing to do.')
        return

    # Create or update Algolia index for the user
    index_users.save_object(to_index_user)


@skip_when_testing
def index_node_save(node_to_index):
    if not current_app.algolia_index_nodes:
        return
    current_app.algolia_index_nodes.save_object(node_to_index)


@skip_when_testing
def index_node_delete(delete_id):
    if current_app.algolia_index_nodes is None:
        return
    current_app.algolia_index_nodes.delete_object(delete_id)
