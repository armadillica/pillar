import logging

from flask import Blueprint, request
import elasticsearch.exceptions as elk_ex
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


def _term_filters(args) -> dict:
    """
    Check if frontent wants to filter stuff
    on specific fields AKA facets

    return mapping with term field name
    and provided user term value
    """
    return {term: args.get(term, '') for term in TERMS}


def _page_index(page) -> int:
    """Return the page index from the query string."""
    try:
        page_idx = int(page)
    except TypeError:
        log.info('invalid page number %r received', request.args.get('page'))
        raise wz_exceptions.BadRequest()
    return page_idx


@blueprint_search.route('/', methods=['GET'])
def search_nodes():
    searchword = request.args.get('q', '')
    project_id = request.args.get('project', '')
    terms = _term_filters(request.args)
    page_idx = _page_index(request.args.get('page', 0))

    result = queries.do_node_search(searchword, terms, page_idx, project_id)
    return jsonify(result)

@blueprint_search.route('/multisearch', methods=['GET'])
def multi_search_nodes():
    import json
    if len(request.args) != 1:
        log.info(f'Expected 1 argument, received {len(request.args)}')

    json_obj = json.loads([a for a in request.args][0])
    q = []
    for row in json_obj:
        q.append({
            'query': row.get('q', ''),
            'project_id': row.get('project', ''),
            'terms': _term_filters(row),
            'page': _page_index(row.get('page', 0))
        })

    result = queries.do_multi_node_search(q)
    return jsonify(result)

@blueprint_search.route('/user')
def search_user():
    searchword = request.args.get('q', '')
    terms = _term_filters(request.args)
    page_idx = _page_index(request.args.get('page', 0))
    # result is the raw elasticseach output.
    # we need to filter fields in case of user objects.

    try:
        result = queries.do_user_search(searchword, terms, page_idx)
    except elk_ex.ElasticsearchException as ex:
        resp = jsonify({'_message': str(ex)})
        resp.status_code = 500
        return resp

    return jsonify(result)


@blueprint_search.route('/admin/user')
@authorization.require_login(require_cap='admin')
def search_user_admin():
    """
    User search over all fields.
    """

    searchword = request.args.get('q', '')
    terms = _term_filters(request.args)
    page_idx = _page_index(_page_index(request.args.get('page', 0)))

    try:
        result = queries.do_user_search_admin(searchword, terms, page_idx)
    except elk_ex.ElasticsearchException as ex:
        resp = jsonify({'_message': str(ex)})
        resp.status_code = 500
        return resp

    return jsonify(result)
