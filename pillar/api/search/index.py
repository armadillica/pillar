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
    index = ''
    doc_types = []
    name = 'remove index'

    def __init__(self):

        if not self.index:
            raise ValueError("No index specified")

        if not self.doc_types:
            raise ValueError("No doc_types specified")

        connections.create_connection(
            hosts=current_app.config['ELASTIC_SEARCH_HOSTS'],
            # sniff_on_start=True,
            retry_on_timeout=True,
        )

    def execute(self):

        idx = es.Index(self.index)

        try:
            idx.delete(ignore=404)
            log.info("Deleted index %s", self.index)
        except AttributeError:
            log.warning("Could not delete index '%s', ignoring", self.index)
        except NotFoundError:
            log.warning("Could not delete index '%s', ignoring", self.index)

        # create doc types
        for dt in self.doc_types:
            idx.doc_type(dt)

        # create index
        idx.create()


class ResetNodeIndex(ResetIndexTask):
    index = current_app.config['ELASTIC_INDICES']['NODE']
    doc_types = [documents.Node]


class ResetUserIndex(ResetIndexTask):
    index = current_app.config['ELASTIC_INDICES']['USER']
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

