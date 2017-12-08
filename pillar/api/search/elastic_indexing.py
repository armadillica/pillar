import logging

from elasticsearch_dsl.connections import connections

from pillar import current_app
from . import documents


elk_hosts = current_app.config['ELASTIC_SEARCH_HOSTS']

connections.create_connection(
    hosts=elk_hosts,
    sniff_on_start=True,
    timeout=20)

log = logging.getLogger(__name__)


def push_updated_user(user_to_index: dict):
    """
    Push an update to the Elastic index when
    a user item is updated.
    """
    doc = documents.create_doc_from_user_data(user_to_index)
    log.debug('UPDATE USER %s', doc._id)
    doc.save()


def index_node_save(node_to_index: dict):

    if not node_to_index:
        return

    doc = documents.create_doc_from_node_data(node_to_index)

    log.debug('CREATED ELK NODE DOC %s', doc._id)
    doc.save()


def index_node_delete(delete_id: str):

    log.debug('NODE DELETE INDEXING %s', delete_id)
    documents.Node(id=delete_id).delete()
