import json
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q
import logging

from pillar import current_app
log = logging.getLogger(__name__)

node_agg_terms = ['node_type', 'media', 'tags', 'is_free']
user_agg_terms = ['roles', ]


class TheELKClient():
    """
    current_app is not available when on import
    """
    client: Elasticsearch = None

    def get_client(self):
        if not self.client:
            self.client = Elasticsearch(
                current_app.config['ELASTIC_SEARCH_HOSTS'])
        else:
            return self.client

elk = TheELKClient()


def add_aggs_to_search(search, agg_terms):
    """
    Add facets / aggregations to the search result
    """

    for term in agg_terms:
        search.aggs.bucket(term, 'terms', field=term)


def make_must(must: list, terms: dict) -> list:
    """ Given term parameters append must queries to the must list """

    for field, value in terms.items():
        if value:
            must.append({'match': {field: value}})

    return must


def nested_bool(must: list, should: list, terms: dict) -> Search:
    """
    Create a nested bool, where the aggregation
    selection is a must
    """
    must = make_must(must, terms)
    bool_query = Q('bool', should=should)
    must.append(bool_query)
    bool_query = Q('bool', must=must)

    search = Search(using=elk.get_client())
    search.query = bool_query

    return search


def do_search(query: str, terms: dict) -> dict:
    """
    Given user query input and term refinements
    search for public published nodes
    """

    should = [
        Q('match', name=query),

        {"match": {"project.name": query}},
        {"match": {"user.name": query}},

        Q('match', description=query),
        Q('term', media=query),
        Q('term', tags=query),
    ]

    must = [
        Q('term', _type='node')
    ]

    if not query:
        should = []

    search = nested_bool(must, should, terms)
    add_aggs_to_search(search, node_agg_terms)

    if log.isEnabledFor(logging.DEBUG):
        print(json.dumps(search.to_dict(), indent=4))

    response = search.execute()

    if log.isEnabledFor(logging.DEBUG):
        print(json.dumps(response.to_dict(), indent=4))

    return response.to_dict()


def do_user_search(query: str, terms: dict) -> dict:
    """ return user objects represented in elasicsearch result dict"""
    should = [
        Q('match', username=query),
        Q('match', full_name=query),
    ]

    must = [
        Q('term', _type='user')
    ]

    # We most likely got and id field. we MUST find it.
    if len(query) == len('563aca02c379cf0005e8e17d'):
        must.append(Q('term', _id=query))

    if not query:
        should = []

    search = nested_bool(must, should, terms)
    add_aggs_to_search(search, user_agg_terms)

    if log.isEnabledFor(logging.DEBUG):
        print(json.dumps(search.to_dict(), indent=4))

    response = search.execute()

    if log.isEnabledFor(logging.DEBUG):
        print(json.dumps(response.to_dict(), indent=4))

    return response.to_dict()


def do_user_search_admin(query: str) -> dict:
    """
    return users seach result dict object
    search all user fields and provide aggregation information
    """
    should = [
        Q('match', username=query),
        Q('match', email=query),
        Q('match', full_name=query),
    ]
    bool_query = Q('bool', should=should)
    search = Search(using=elk.get_client())
    search.query = bool_query

    if log.isEnabledFor(logging.DEBUG):
        log.debug(json.dumps(search.to_dict(), indent=4))

    response = search.execute()

    if log.isEnabledFor(logging.DEBUG):
        log.debug(json.dumps(response.to_dict(), indent=4))

    return response.to_dict()
