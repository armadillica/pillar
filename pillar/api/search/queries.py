import json
import logging
import typing

from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q, MultiSearch
from elasticsearch_dsl.query import Query

from pillar import current_app

log = logging.getLogger(__name__)

BOOLEAN_TERMS = ['is_free']
NODE_AGG_TERMS = ['node_type', 'media', 'tags', *BOOLEAN_TERMS]
USER_AGG_TERMS = ['roles', ]
ITEMS_PER_PAGE = 10
USER_SOURCE_INCLUDE = ['full_name', 'objectID', 'username']

# Will be set in setup_app()
client: Elasticsearch = None


def add_aggs_to_search(search, agg_terms):
    """
    Add facets / aggregations to the search result
    """

    for term in agg_terms:
        search.aggs.bucket(term, 'terms', field=term)


def make_filter(must: list, terms: dict) -> list:
    """ Given term parameters append must queries to the must list """

    for field, value in terms.items():
        if value not in (None, ''):
            must.append({'term': {field: value}})

    return must


def nested_bool(filters: list, should: list, terms: dict, *, index_alias: str) -> Search:
    """
    Create a nested bool, where the aggregation selection is a must.

    :param index_alias: 'USER' or 'NODE', see ELASTIC_INDICES config.
    """
    filters = make_filter(filters, terms)
    bool_query = Q('bool', should=should)
    bool_query = Q('bool', must=bool_query, filter=filters)

    index = current_app.config['ELASTIC_INDICES'][index_alias]
    search = Search(using=client, index=index)
    search.query = bool_query

    return search


def do_multi_node_search(queries: typing.List[dict]) -> typing.List[dict]:
    """
    Given user query input and term refinements
    search for public published nodes
    """
    search = create_multi_node_search(queries)
    return _execute_multi(search)


def do_node_search(query: str, terms: dict, page: int, project_id: str='') -> dict:
    """
    Given user query input and term refinements
    search for public published nodes
    """
    search = create_node_search(query, terms, page, project_id)
    return _execute(search)


def create_multi_node_search(queries: typing.List[dict]) -> MultiSearch:
    search = MultiSearch(using=client)
    for q in queries:
        search = search.add(create_node_search(**q))

    return search


def create_node_search(query: str, terms: dict, page: int, project_id: str='') -> Search:
    terms = _transform_terms(terms)
    should = [
        Q('match', name=query),

        {"match": {"project.name": query}},
        {"match": {"user.name": query}},

        Q('match', description=query),
        Q('term', media=query),
        Q('term', tags=query),
    ]
    filters = []
    if project_id:
        filters.append({'term': {'project.id': project_id}})
    if not query:
        should = []
    search = nested_bool(filters, should, terms, index_alias='NODE')
    if not query:
        search = search.sort('-created_at')
    add_aggs_to_search(search, NODE_AGG_TERMS)
    search = paginate(search, page)
    if log.isEnabledFor(logging.DEBUG):
        log.debug(json.dumps(search.to_dict(), indent=4))
    return search


def do_user_search(query: str, terms: dict, page: int) -> dict:
    """ return user objects represented in elasicsearch result dict"""

    search = create_user_search(query, terms, page)
    return _execute(search)


def _common_user_search(query: str) -> (typing.List[Query], typing.List[Query]):
    """Construct (filter,should) for regular + admin user search."""
    if not query:
        return [], []

    should = []

    if '@' in query:
        should.append({'term': {'email_exact': {'value': query, 'boost': 50}}})
        email_boost = 25
    else:
        email_boost = 1

    should.extend([
        Q('match', username=query),
        Q('match', full_name=query),
        {'match': {'email': {'query': query, 'boost': email_boost}}},
        {'term': {'username_exact': {'value': query, 'boost': 50}}},
    ])

    return [], should


def do_user_search_admin(query: str, terms: dict, page: int) -> dict:
    """
    return users seach result dict object
    search all user fields and provide aggregation information
    """

    search = create_user_admin_search(query, terms, page)
    return _execute(search)


def _execute(search: Search) -> dict:
    if log.isEnabledFor(logging.DEBUG):
        log.debug(json.dumps(search.to_dict(), indent=4))
    resp = search.execute()
    if log.isEnabledFor(logging.DEBUG):
        log.debug(json.dumps(resp.to_dict(), indent=4))
    return resp.to_dict()


def _execute_multi(search: typing.List[Search]) -> typing.List[dict]:
    if log.isEnabledFor(logging.DEBUG):
        log.debug(json.dumps(search.to_dict(), indent=4))
    resp = search.execute()
    if log.isEnabledFor(logging.DEBUG):
        log.debug(json.dumps(resp.to_dict(), indent=4))
    return [r.to_dict() for r in resp]


def create_user_admin_search(query: str, terms: dict, page: int) -> Search:
    terms = _transform_terms(terms)
    filters, should = _common_user_search(query)
    if query:
        # We most likely got and id field. we should find it.
        if len(query) == len('563aca02c379cf0005e8e17d'):
            should.append({'term': {
                'objectID': {
                    'value': query,  # the thing we're looking for
                    'boost': 100,  # how much more it counts for the score
                }
            }})
    search = nested_bool(filters, should, terms, index_alias='USER')
    add_aggs_to_search(search, USER_AGG_TERMS)
    search = paginate(search, page)
    return search


def create_user_search(query: str, terms: dict, page: int) -> Search:
    search = create_user_admin_search(query, terms, page)
    return search.source(include=USER_SOURCE_INCLUDE)


def paginate(search: Search, page_idx: int) -> Search:
    return search[page_idx * ITEMS_PER_PAGE:(page_idx + 1) * ITEMS_PER_PAGE]


def _transform_terms(terms: dict) -> dict:
    """
    Ugly hack! Elastic uses 1/0 for boolean values in its aggregate response,
    but expects true/false in queries.
    """
    transformed = terms.copy()
    for t in BOOLEAN_TERMS:
        orig = transformed.get(t)
        if orig in ('1', '0'):
            transformed[t] = bool(int(orig))
    return transformed


def setup_app(app):
    global client

    hosts = app.config['ELASTIC_SEARCH_HOSTS']
    log.getChild('setup_app').info('Creating ElasticSearch client for %s', hosts)
    client = Elasticsearch(hosts)
