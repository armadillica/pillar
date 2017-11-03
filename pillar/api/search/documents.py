import logging

import elasticsearch_dsl as es
from elasticsearch_dsl import analysis
# from pillar import current_app

# define elasticsearch document mapping.


log = logging.getLogger(__name__)


edge_ngram_filter = analysis.token_filter(
    'edge_ngram_filter',
    type='edge_ngram',
    min_gram=1,
    max_gram=15
)


autocomplete = es.analyzer(
    'autocomplete',
    tokenizer='standard',
    filter=['lowercase', edge_ngram_filter]
)


class User(es.DocType):
    """
    Elastic document describing user
    """

    name = es.String(
        fielddata=True,
        analyzer=autocomplete,
    )


class Node(es.DocType):
    """
    Elastic document describing user
    """

    node_type = es.Keyword()

    x_code = es.String(
        multi=True,
        fielddata=True,
        analyzer=autocomplete,
    )


def create_doc_from_user_data(user_to_index):
    doc_id = user_to_index['objectID']
    doc = User(_id=doc_id)
    return doc


def create_doc_from_node_data(node_to_index):

    # node stuff
    doc_id = node_to_index['objectID']
    doc = Node(_id=doc_id)
    doc.node_type = node_to_index['node_type']

    return doc
