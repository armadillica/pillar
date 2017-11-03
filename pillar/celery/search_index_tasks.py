import logging
from pillar import current_app

from . import algolia_indexing
# from . import elastic_indexing


log = logging.getLogger(__name__)

# TODO(stephan) make index backend conditional on settings.

SEARCH_BACKENDS = {
    'algolia': algolia_indexing,
    'elastic': None,  # elastic_indexing
}


@current_app.celery.task(ignore_result=True)
def updated_user(user_id: str):
    """Push an update to the index when a user item is updated"""

    algolia_indexing.push_updated_user(user_id)


@current_app.celery.task(ignore_result=True)
def node_save(node_id: str):

    algolia_indexing.index_node_save(node_id)


@current_app.celery.task(ignore_result=True)
def node_delete(node_id: str):

    algolia_indexing.index_node_delete(node_id)



def build_doc_to_index_from(node: dict):
    """
    Given node build an to_index document
    """
    pass



