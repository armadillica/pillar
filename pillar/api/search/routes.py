import logging

from flask import Blueprint, request
from werkzeug import exceptions as wz_exceptions
from pillar.api.utils import authorization, jsonify

from . import queries

log = logging.getLogger(__name__)

blueprint_search = Blueprint('elksearch', __name__)



def _valid_search() -> str:
    """
    Returns search parameters, raising error when missing.
    """

    searchword = request.args.get('q', '')
    # if not searchword:
    #    raise wz_exceptions.BadRequest(
    #        'You are forgetting a "?q=whatareyoulookingfor"')
    return searchword


def _term_filters() -> dict:
    """
    Check if frontent wants to filter stuff
    on specific fields AKA facets
    """

    terms = [
        'node_type', 'media',
        'tags', 'is_free', 'projectname',
        'roles',
    ]

    parsed_terms = {}

    for term in terms:
        parsed_terms[term] = request.args.get(term, '')

    return parsed_terms


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
