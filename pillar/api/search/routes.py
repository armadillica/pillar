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


def _valid_search() -> [str, str]:
    """
    Validate search parameters
    """

    searchword = request.args.get('q', '')

    if not searchword:
        return '', 'You are forgetting a "?q=whatareyoulookingfor"'

    return searchword, ''


@blueprint_search.route('/', methods=['GET'])
def search_nodes():

    searchword, err = _valid_search()
    if err:
        return err

    data = queries.do_search(searchword)

    resp = Response(json.dumps(data), mimetype='application/json')
    return resp


@blueprint_search.route('/user', methods=['GET'])
def search_user():

    searchword, err = _valid_search()
    if err:
        return err

    data = queries.do_user_search(searchword)

    resp = Response(json.dumps(data), mimetype='application/json')
    return resp


@authorization.require_login(require_cap='admin')
@blueprint_search.route('/admin/user', methods=['GET'])
def search_user_admin():
    """
    User search over all fields.
    """

    searchword, err = _valid_search()
    if err:
        return err

    data = queries.do_user_search_admin(searchword)

    resp = Response(json.dumps(data), mimetype='application/json')
    return resp
