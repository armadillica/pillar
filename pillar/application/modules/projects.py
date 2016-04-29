import copy
import logging
import json

from eve.methods.post import post_internal
from eve.methods.patch import patch_internal
from flask import g, Blueprint, request, abort, current_app

from application.utils import remove_private_keys, authorization, PillarJSONEncoder
from application.utils.gcs import GoogleCloudStorageBucket
from application.utils.authorization import user_has_role, check_permissions
from manage_extra.node_types.asset import node_type_asset
from manage_extra.node_types.blog import node_type_blog
from manage_extra.node_types.comment import node_type_comment
from manage_extra.node_types.group import node_type_group
from manage_extra.node_types.page import node_type_page
from manage_extra.node_types.post import node_type_post

log = logging.getLogger(__name__)
blueprint = Blueprint('projects', __name__)


def before_inserting_projects(items):
    """Strip unwanted properties, that will be assigned after creation. Also,
    verify permission to create a project (check quota, check role).

    :param items: List of project docs that have been inserted (normally one)
    """

    # Allow admin users to do whatever they want.
    if user_has_role(u'admin'):
        return

    for item in items:
        item.pop('url', None)


def before_edit_check_permissions(document, original):
    # Allow admin users to do whatever they want.
    # TODO: possibly move this into the check_permissions function.
    if user_has_role(u'admin'):
        return

    check_permissions(original, request.method)


def before_delete_project(document):
    """Checks permissions before we allow deletion"""

    # Allow admin users to do whatever they want.
    # TODO: possibly move this into the check_permissions function.
    if user_has_role(u'admin'):
        return

    check_permissions(document, request.method)


def protect_sensitive_fields(document, original):
    """When not logged in as admin, prevents update to certain fields."""

    # Allow admin users to do whatever they want.
    if user_has_role(u'admin'):
        return

    def revert(name):
        if name not in original:
            try:
                del document[name]
            except KeyError:
                pass
            return
        document[name] = original[name]

    revert('url')
    revert('is_private')
    revert('status')
    revert('category')
    revert('user')


def after_inserting_projects(items):
    """After inserting a project in the collection we do some processing such as:
    - apply the right permissions
    - define basic node types
    - optionally generate a url
    - initialize storage space

    :param items: List of project docs that have been inserted (normally one)
    """
    current_user = g.current_user
    users_collection = current_app.data.driver.db['users']
    user = users_collection.find_one(current_user['user_id'])

    for item in items:
        after_inserting_project(item, user)


def after_inserting_project(project, db_user):
    project_id = project['_id']
    user_id = db_user['_id']

    # Create a project-specific admin group (with name matching the project id)
    result, _, _, status = post_internal('groups', {'name': str(project_id)})
    if status != 201:
        log.error('Unable to create admin group for new project %s: %s',
                  project_id, result)
        return abort_with_error(status)

    admin_group_id = result['_id']
    log.info('Created admin group %s for project %s', admin_group_id, project_id)

    # Assign the current user to the group
    db_user.setdefault('groups', []).append(admin_group_id)

    result, _, _, status = patch_internal('users', {'groups': db_user['groups']}, _id=user_id)
    if status != 200:
        log.error('Unable to add user %s as member of admin group %s for new project %s: %s',
                  user_id, admin_group_id, project_id, result)
        return abort_with_error(status)
    log.debug('Made user %s member of group %s', user_id, admin_group_id)

    # Assign the group to the project with admin rights
    permissions = {
        'world': ['GET'],
        'users': [],
        'groups': [
            {'group': admin_group_id,
             'methods': ['GET', 'PUT', 'POST', 'DELETE']},
        ]
    }

    def with_permissions(node_type):
        copied = copy.deepcopy(node_type)
        copied['permissions'] = permissions
        return copied

    # Assign permissions to the project itself, as well as to the node_types
    project['permissions'] = permissions
    project['node_types'] = [
        with_permissions(node_type_group),
        with_permissions(node_type_asset),
        with_permissions(node_type_comment)]

    # Allow admin users to use whatever url they want.
    if not user_has_role(u'admin') or not project.get('url'):
        project['url'] = "p-{!s}".format(project_id)

    # Initialize storage page (defaults to GCS)
    if current_app.config.get('TESTING'):
        log.warning('Not creating Google Cloud Storage bucket while running unit tests!')
    else:
        gcs_storage = GoogleCloudStorageBucket(str(project_id))
        if gcs_storage.bucket.exists():
            log.info('Created CGS instance for project %s', project_id)
        else:
            log.warning('Unable to create CGS instance for project %s', project_id)

    # Commit the changes directly to the MongoDB; a PUT is not allowed yet,
    # as the project doesn't have a valid permission structure.
    projects_collection = current_app.data.driver.db['projects']
    result = projects_collection.update_one({'_id': project_id},
                                            {'$set': remove_private_keys(project)})
    if result.matched_count != 1:
        log.warning('Unable to update project %s: %s', project_id, result.raw_result)
        abort_with_error(500)


def _create_new_project(project_name, user_id, overrides):
    """Creates a new project owned by the given user."""

    log.info('Creating new project "%s" for user %s', project_name, user_id)

    # Create the project itself, the rest will be done by the after-insert hook.
    project = {'description': '',
               'name': project_name,
               'node_types': [],
               'status': 'published',
               'user': user_id,
               'is_private': True,
               'permissions': {},
               'url': '',
               'summary': '',
               'category': 'assets',  # TODO: allow the user to choose this.
               }
    if overrides is not None:
        project.update(overrides)

    result, _, _, status = post_internal('projects', project)
    if status != 201:
        log.error('Unable to create project "%s": %s', project_name, result)
        return abort_with_error(status)
    project.update(result)

    # Now re-fetch the etag, as both the initial document and the returned
    # result do not contain the same etag as the database.
    document = current_app.data.driver.db['projects'].find_one(project['_id'],
                                                               projection={'_etag': 1})
    project.update(document)

    log.info('Created project %s for user %s', project['_id'], user_id)

    return project


@blueprint.route('/create', methods=['POST'])
@authorization.require_login(require_roles={'admin', 'subscriber'})
def create_project(overrides=None):
    """Creates a new project."""

    project_name = request.form['project_name']
    user_id = g.current_user['user_id']

    project = _create_new_project(project_name, user_id, overrides)

    # Return the project in the response.
    resp = current_app.response_class(json.dumps(project, cls=PillarJSONEncoder),
                                      mimetype='application/json',
                                      status=201,
                                      headers={'Location': '/projects/%s' % project['_id']})
    return resp


def abort_with_error(status):
    """Aborts with the given status, or 500 if the status doesn't indicate an error.

    If the status is < 400, status 500 is used instead.
    """

    abort(status if status // 100 >= 4 else 500)


def setup_app(app, url_prefix):
    app.on_replace_projects += before_edit_check_permissions
    app.on_replace_projects += protect_sensitive_fields
    app.on_update_projects += before_edit_check_permissions
    app.on_update_projects += protect_sensitive_fields
    app.on_delete_item_projects += before_delete_project
    app.on_insert_projects += before_inserting_projects
    app.on_inserted_projects += after_inserting_projects
    app.register_blueprint(blueprint, url_prefix=url_prefix)
