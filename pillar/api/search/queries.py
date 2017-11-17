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


def do_search(query: str) -> dict:
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
    bool_query = Q('bool', should=should)
    search = Search(using=client)
    search.query = bool_query

    if current_app.config['DEBUG']:
        log.debug(json.dumps(search.to_dict(), indent=4))

    response = search.execute()

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

    return response.to_dict()
