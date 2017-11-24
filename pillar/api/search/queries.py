import logging
import json
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q
from elasticsearch_dsl.connections import connections

from pillar import current_app

#elk_hosts = current_app.config['ELASTIC_SEARCH_HOSTS']
#
#connections.create_connection(
#    hosts=elk_hosts,
#    sniff_on_start=True,
#    timeout=20)
#
client = Elasticsearch()

log = logging.getLogger(__name__)



def add_aggs_to_search(search):
    """
    """

    agg_terms = ['node_type', 'media', 'tags', 'is_free']

    for term in agg_terms:
        search.aggs.bucket(term, 'terms', field=term)

    #search.aggs.bucket('project', 'terms', field='project.name')


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

    #must = []

    #for field, value in terms.items():
    #    must.append(

    bool_query = Q('bool', should=should)
    search = Search(using=client)
    search.query = bool_query

    add_aggs_to_search(search)

    if current_app.config['DEBUG']:
        print(json.dumps(search.to_dict(), indent=4))

    response = search.execute()

    if current_app.config['DEBUG']:
        print(json.dumps(response.to_dict(), indent=4))

    return response.to_dict()


def do_user_search(query: str) -> dict:
    """
    return user objects
    """
    should = [
        Q('match', username=query),
        Q('match', full_name=query),
    ]
    bool_query = Q('bool', should=should)
    search = Search(using=client)
    search.query = bool_query

    if current_app.config['DEBUG']:
        log.debug(json.dumps(search.to_dict(), indent=4))

    response = search.execute()

    if current_app.config['DEBUG']:
        log.debug('%s', json.dumps(response.to_dict(), indent=4))

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
