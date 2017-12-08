import logging
import json
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q

from pillar import current_app

client = Elasticsearch()

log = logging.getLogger(__name__)

node_agg_terms = ['node_type', 'media', 'tags', 'is_free']
user_agg_terms = ['roles', ]


def add_aggs_to_search(search, agg_terms):
    """
    Add facets / aggregations to the search result
    """

    for term in agg_terms:
        search.aggs.bucket(term, 'terms', field=term)


def make_must(must: list, terms: dict) -> list:
    """
    Given some term parameters
    we must match those
    """

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

    search = Search(using=client)
    search.query = bool_query

    return search


def do_search(query: str, terms: dict) -> dict:
    """
    Given user input search for node/stuff
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

    if current_app.config['DEBUG']:
        print(json.dumps(search.to_dict(), indent=4))

    response = search.execute()

    if current_app.config['DEBUG']:
        print(json.dumps(response.to_dict(), indent=4))

    return response.to_dict()


def do_user_search(query: str, terms: dict) -> dict:
    """
    return user objects
    """
    should = [
        Q('match', username=query),
        Q('match', full_name=query),
    ]

    must = [
        Q('term', _type='user')
    ]

    # We got an id field. we MUST find it.
    if len(query) == len('563aca02c379cf0005e8e17d'):
        must.append(Q('term', _id=query))

    if not query:
        should = []

    search = nested_bool(must, should, terms)
    add_aggs_to_search(search, user_agg_terms)

    if current_app.config['DEBUG']:
        print(json.dumps(search.to_dict(), indent=4))

    response = search.execute()

    if current_app.config['DEBUG']:
        print(json.dumps(response.to_dict(), indent=4))

    return response.to_dict()


def do_user_search_admin(query: str) -> dict:
    """
    return users with all fields and aggregations
    """
    should = [
        Q('match', username=query),
        Q('match', email=query),
        Q('match', full_name=query),
    ]
    bool_query = Q('bool', should=should)
    search = Search(using=client)
    search.query = bool_query

    if current_app.config['DEBUG']:
        log.debug(json.dumps(search.to_dict(), indent=4))

    response = search.execute()

    if current_app.config['DEBUG']:
        log.debug(json.dumps(response.to_dict(), indent=4))

    return response.to_dict()
