import logging
# import time

# from elasticsearch import helpers
# import elasticsearch

# from elasticsearch.client import IndicesClient

from elasticsearch.exceptions import NotFoundError
from elasticsearch_dsl.connections import connections
import elasticsearch_dsl as es

from pillar import current_app

from . import documents

log = logging.getLogger(__name__)


class ResetIndexTask(object):
    """
    Clear and build index / mapping
    """
    index_key = ''
    """Key into the ELASTIC_INDICES dict in the app config."""

    doc_types = []
    name = 'remove index'

    def __init__(self):

        if not self.index_key:
            raise ValueError("No index specified")

        if not self.doc_types:
            raise ValueError("No doc_types specified")

        connections.create_connection(
            hosts=current_app.config['ELASTIC_SEARCH_HOSTS'],
            # sniff_on_start=True,
            retry_on_timeout=True,
        )

    def execute(self):
        index = current_app.config['ELASTIC_INDICES'][self.index_key]
        idx = es.Index(index)

        try:
            idx.delete(ignore=404)
            log.info("Deleted index %s", index)
        except AttributeError:
            log.warning("Could not delete index '%s', ignoring", index)
        except NotFoundError:
            log.warning("Could not delete index '%s', ignoring", index)

        # create doc types
        for dt in self.doc_types:
            idx.doc_type(dt)

        # create index
        idx.create()


class ResetNodeIndex(ResetIndexTask):
    index_key = 'NODE'
    doc_types = [documents.Node]


class ResetUserIndex(ResetIndexTask):
    index_key = 'USER'
    doc_types = [documents.User]
def reset_node_index():
    resettask = ResetNodeIndex()
    resettask.execute()


def reset_index(indexnames):
    if 'users' in indexnames:
        resettask = ResetUserIndex()
        resettask.execute()
    if 'nodes' in indexnames:
        resettask = ResetUserIndex()
        resettask.execute()

