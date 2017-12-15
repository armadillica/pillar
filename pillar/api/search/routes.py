import logging

from flask import Blueprint, request
from werkzeug import exceptions as wz_exceptions
from pillar.api.utils import authorization, jsonify

from . import queries

log = logging.getLogger(__name__)

blueprint_search = Blueprint('elksearch', __name__)


terms = [
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
    return {term: request.args.get(term, '')  for term in terms}


@blueprint_search.route('/')
def search_nodes():
    searchword = _valid_search()
    terms = _term_filters()
    data = queries.do_search(searchword, terms)
    return jsonify(data)


@blueprint_search.route('/user')
def search_user():
    searchword = _valid_search()
    terms = _term_filters()
    data = queries.do_user_search(searchword, terms)
    return jsonify(data)


@blueprint_search.route('/admin/user')
@authorization.require_login(require_cap='admin')
def search_user_admin():
    """
    User search over all fields.
    """

    searchword = _valid_search()

    data = queries.do_user_search_admin(searchword)

    return jsonify(data)
