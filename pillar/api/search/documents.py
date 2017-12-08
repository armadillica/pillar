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
    """Elastic document describing user."""

    objectID = es.Keyword()

    username = es.String(
        fielddata=True,
        analyzer=autocomplete,
    )

    full_name = es.String(
        fielddata=True,
        analyzer=autocomplete,
    )

    roles = es.Keyword(multi=True)
    groups = es.Keyword(multi=True)

    email = es.String(
        fielddata=True,
        analyzer=autocomplete,
    )

    class Meta:
        index = 'users'


class Node(es.DocType):
    """
    Elastic document describing user
    """

    node_type = es.Keyword()

    objectID = es.Keyword()

    name = es.String(
        fielddata=True,
        analyzer=autocomplete
    )

    user = es.Object({
        'fields': {
            'id': es.Keyword(),
            'name':  es.String(
                fielddata=True,
                analyzer=autocomplete)
        }
    })

    description = es.String()

    is_free = es.Boolean()

    project = es.Object({
        'fields': {
            'id': es.Keyword(),
            'name': es.Keyword(),
        }
    })

    media = es.Keyword()

    picture = es.Keyword()

    tags = es.Keyword(multi=True)
    license_notes = es.String()

    created_at = es.Date()
    updated_at = es.Date()

    class Meta:
        index = 'nodes'


def create_doc_from_user_data(user_to_index):
    doc_id = str(user_to_index['objectID'])
    doc = User(_id=doc_id)
    doc.objectID = str(user_to_index['objectID'])
    doc.username = user_to_index['username']
    doc.full_name = user_to_index['full_name']
    doc.roles = list(map(str, user_to_index['roles']))
    doc.groups = list(map(str, user_to_index['groups']))
    doc.email = user_to_index['email']
    return doc


def create_doc_from_node_data(node_to_index):

    # node stuff
    doc_id = str(node_to_index.get('objectID', ''))

    if not doc_id:
        log.error('ID missing %s', node_to_index)
        return

    doc = Node(_id=doc_id)

    doc.objectID = str(node_to_index['objectID'])
    doc.node_type = node_to_index['node_type']
    doc.name = node_to_index['name']
    doc.user.id = str(node_to_index['user']['_id'])
    doc.user.name = node_to_index['user']['full_name']
    doc.project.id = str(node_to_index['project']['_id'])
    doc.project.name = node_to_index['project']['name']

    if node_to_index['node_type'] == 'asset':
        doc.media = node_to_index['media']

    doc.picture = node_to_index.get('picture')

    doc.tags = node_to_index.get('tags')
    doc.license_notes = node_to_index.get('license_notes')

    doc.created_at = node_to_index['created']
    doc.updated_at = node_to_index['updated']

    return doc


def create_doc_from_user(user_to_index: dict) -> User:
    """
    Create a user document from user
    """

    doc_id = str(user_to_index['objectID'])
    doc = User(_id=doc_id)
    doc.objectID = str(user_to_index['objectID'])
    doc.full_name = user_to_index['full_name']
    doc.username = user_to_index['username']
    doc.roles = user_to_index['roles']
    doc.groups = user_to_index['groups']
    doc.email = user_to_index['email']

    return doc
