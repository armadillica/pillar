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

#@authorization.require_login(require_cap='subscriber')
@blueprint_search.route('/', methods=['GET'])
def search_nodes():

    searchword = request.args.get('q', '')

    if not searchword:
        return 'You are forgetting a "?q=whatareyoulookingfor"'

    data = queries.do_search(searchword)

    resp = Response(json.dumps(data), mimetype='application/json')
    return resp
