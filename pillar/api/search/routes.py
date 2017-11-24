import json
import logging

from bson import ObjectId
from flask import Blueprint, request, current_app, make_response, url_for
from flask import Response
from werkzeug import exceptions as wz_exceptions

from pillar.api.utils import authorization, jsonify, str2id
from pillar.api.utils import mongo
from pillar.api.utils.authorization import require_login, check_permissions
from pillar.auth import current_user


log = logging.getLogger(__name__)

blueprint_search = Blueprint('elksearch', __name__)

from . import queries


def _valid_search() -> str:
    """
    Returns search parameters, raising error when missing.
    """

    searchword = request.args.get('q', '')
    if not searchword:
        raise wz_exceptions.BadRequest('You are forgetting a "?q=whatareyoulookingfor"')
    return searchword


def _term_filters() -> dict:
    """
    Check if frontent want to filter stuff
    """

    terms = [
        'node_type', 'media',
        'tags', 'is_free', 'projectname']

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

    data = queries.do_user_search(searchword)

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
