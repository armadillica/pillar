import json
import logging

from bson import ObjectId
from flask import Blueprint, g, request, current_app, make_response, url_for
from pillar.api.utils import authorization, jsonify, str2id
from pillar.api.utils import mongo
from pillar.api.utils.authorization import require_login, check_permissions
from werkzeug import exceptions as wz_exceptions

from . import utils

log = logging.getLogger(__name__)

blueprint_api = Blueprint('projects_api', __name__)


@blueprint_api.route('/create', methods=['POST'])
@authorization.require_login(require_cap='subscriber')
def create_project(overrides=None):
    """Creates a new project."""

    if request.mimetype == 'application/json':
        project_name = request.json['name']
    else:
        project_name = request.form['project_name']
    user_id = g.current_user['user_id']

    project = utils.create_new_project(project_name, user_id, overrides)

    # Return the project in the response.
    loc = url_for('projects|item_lookup', _id=project['_id'])
    return jsonify(project, status=201, headers={'Location': loc})


@blueprint_api.route('/users', methods=['GET', 'POST'])
@authorization.require_login()
def project_manage_users():
    """Manage users of a project. In this initial implementation, we handle
    addition and removal of a user to the admin group of a project.
    No changes are done on the project itself.
    """

    from pillar.api.utils import str2id

    projects_collection = current_app.data.driver.db['projects']
    users_collection = current_app.data.driver.db['users']

    # TODO: check if user is admin of the project before anything
    if request.method == 'GET':
        project_id = request.args['project_id']
        project = projects_collection.find_one({'_id': ObjectId(project_id)})
        admin_group_id = project['permissions']['groups'][0]['group']

        users = users_collection.find(
            {'groups': {'$in': [admin_group_id]}},
            {'username': 1, 'email': 1, 'full_name': 1})
        return jsonify({'_status': 'OK', '_items': list(users)})

    # The request is not a form, since it comes from the API sdk
    data = json.loads(request.data)
    project_id = str2id(data['project_id'])
    target_user_id = str2id(data['user_id'])
    action = data['action']
    current_user_id = g.current_user['user_id']

    project = projects_collection.find_one({'_id': project_id})

    # Check if the current_user is owner of the project, or removing themselves.
    if not authorization.user_has_role('admin'):
        remove_self = target_user_id == current_user_id and action == 'remove'
        if project['user'] != current_user_id and not remove_self:
            utils.abort_with_error(403)

    admin_group = utils.get_admin_group(project)

    # Get the user and add the admin group to it
    if action == 'add':
        operation = '$addToSet'
        log.info('project_manage_users: Adding user %s to admin group of project %s',
                 target_user_id, project_id)
    elif action == 'remove':
        log.info('project_manage_users: Removing user %s from admin group of project %s',
                 target_user_id, project_id)
        operation = '$pull'
    else:
        log.warning('project_manage_users: Unsupported action %r called by user %s',
                    action, current_user_id)
        raise wz_exceptions.UnprocessableEntity()

    users_collection.update({'_id': target_user_id},
                            {operation: {'groups': admin_group['_id']}})

    user = users_collection.find_one({'_id': target_user_id},
                                     {'username': 1, 'email': 1,
                                      'full_name': 1})

    if not user:
        return jsonify({'_status': 'ERROR'}), 404

    user['_status'] = 'OK'
    return jsonify(user)


@blueprint_api.route('/<string:project_id>/quotas')
@require_login()
def project_quotas(project_id):
    """Returns information about the project's limits."""

    # Check that the user has GET permissions on the project itself.
    project = mongo.find_one_or_404('projects', project_id)
    check_permissions('projects', project, 'GET')

    file_size_used = utils.project_total_file_size(project_id)

    info = {
        'file_size_quota': None,  # TODO: implement this later.
        'file_size_used': file_size_used,
    }

    return jsonify(info)


@blueprint_api.route('/<project_id>/<node_type>', methods=['OPTIONS', 'GET'])
def get_allowed_methods(project_id=None, node_type=None):
    """Returns allowed methods to create a node of a certain type.

    Either project_id or parent_node_id must be given. If the latter is given,
    the former is deducted from it.
    """

    project = mongo.find_one_or_404('projects', str2id(project_id))
    proj_methods = authorization.compute_allowed_methods('projects', project, node_type)

    resp = make_response()
    resp.headers['Allowed'] = ', '.join(sorted(proj_methods))
    resp.status_code = 204

    return resp


