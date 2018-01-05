import logging

from elasticsearch_dsl.connections import connections
from elasticsearch.exceptions import NotFoundError

from pillar import current_app
from . import documents

log = logging.getLogger(__name__)

elk_hosts = current_app.config['ELASTIC_SEARCH_HOSTS']

connections.create_connection(
    hosts=elk_hosts,
    sniff_on_start=False,
    timeout=20)


def push_updated_user(user_to_index: dict):
    """
    Push an update to the Elastic index when a user item is updated.
    """
    if not user_to_index:
        return

    doc = documents.create_doc_from_user_data(user_to_index)

    if not doc:
        return

    log.debug('Index update user doc elasticsearch %s.', doc._id)
    doc.save()


def index_node_save(node_to_index: dict):
    """
    Push an update to the Elastic index when a node item is saved.
    """
    if not node_to_index:
        return

    doc = documents.create_doc_from_node_data(node_to_index)

    if not doc:
        return

    log.debug('Index created node doc elasticsearch %s.', doc._id)
    doc.save()


def index_node_delete(delete_id: str):
    """
    Delete node document from Elastic index useing a node id
    """
    log.debug('Index node doc delete %s', delete_id)

    try:
        doc = documents.Node.get(id=delete_id)
        doc.delete()
    except NotFoundError:
        # seems to be gone already..
        pass
