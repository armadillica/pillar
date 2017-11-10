import logging
from pillar import current_app
from elasticsearch_dsl.connections import connections

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

    log.warning(
        'WIP USER ELK INDEXING %s %s',
        user_to_index.get('username'),
        user_to_index.get('objectID'))


def index_node_save(node_to_index: dict):

    log.warning(
        'ELK NODE INDEXING %s',
        node_to_index.get('objectID'))

    log.warning(node_to_index)

    doc = documents.create_doc_from_node_data(node_to_index)

    log.warning('CREATED ELK DOC')
    doc.save()


def index_node_delete(delete_id: str):

    log.warning('NODE DELETE INDEXING %s', delete_id)
    documents.Node(id=delete_id).delete()
