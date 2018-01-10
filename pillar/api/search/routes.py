import logging

from flask import Blueprint, request
from werkzeug import exceptions as wz_exceptions
from pillar.api.utils import authorization, jsonify

from . import queries

log = logging.getLogger(__name__)

blueprint_search = Blueprint('elksearch', __name__)

TERMS = [
    'node_type', 'media',
    'tags', 'is_free', 'projectname',
    'roles',
]


def _valid_search() -> str:
    """ Returns search parameters """
    query = request.args.get('q', '')
    return query


def _term_filters() -> dict:
    """
    Check if frontent wants to filter stuff
    on specific fields AKA facets

    return mapping with term field name
    and provided user term value
    """
    return {term: request.args.get(term, '') for term in TERMS}


def _page_index() -> int:
    """Return the page index from the query string."""
    try:
        page_idx = int(request.args.get('page') or '0')
    except TypeError:
        log.info('invalid page number %r received', request.args.get('page'))
        raise wz_exceptions.BadRequest()
    return page_idx


@blueprint_search.route('/')
def search_nodes():
    searchword = _valid_search()
    terms = _term_filters()
    page_idx = _page_index()

    result = queries.do_node_search(searchword, terms, page_idx)
    return jsonify(result)


@blueprint_search.route('/user')
def search_user():
    searchword = _valid_search()
    terms = _term_filters()
    page_idx = _page_index()
    # result is the raw elasticseach output.
    # we need to filter fields in case of user objects.
    result = queries.do_user_search(searchword, terms, page_idx)

    # filter sensitive stuff
    # we only need. objectID, full_name, username
    hits = result.get('hits', {})

    new_hits = []

    for hit in hits.get('hits'):
        source = hit['_source']
        single_hit = {
            '_source': {
                'objectID': source.get('objectID'),
                'username': source.get('username'),
                'full_name': source.get('full_name'),
            }
        }

        new_hits.append(single_hit)

    # replace search result with safe subset
    result['hits']['hits'] = new_hits

    return jsonify(result)


@blueprint_search.route('/admin/user')
@authorization.require_login(require_cap='admin')
def search_user_admin():
    """
    User search over all fields.
    """

    searchword = _valid_search()
    terms = _term_filters()
    page_idx = _page_index()
    result = queries.do_user_search_admin(searchword, terms, page_idx)

    return jsonify(result)
