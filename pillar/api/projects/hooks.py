import copy
import logging

from flask import request, abort, current_app
from gcloud import exceptions as gcs_exceptions

from pillar.api.node_types.asset import node_type_asset
from pillar.api.node_types.comment import node_type_comment
from pillar.api.node_types.group import node_type_group
from pillar.api.node_types.group_texture import node_type_group_texture
from pillar.api.node_types.texture import node_type_texture
from pillar.api.file_storage_backends import default_storage_backend
from pillar.api.file_storage_backends.gcs import GoogleCloudStorageBucket
from pillar.api.utils import authorization, authentication
from pillar.api.utils import remove_private_keys
from pillar.api.utils.authorization import user_has_role, check_permissions
from .utils import abort_with_error

log = logging.getLogger(__name__)

# Default project permissions for the admin group.
DEFAULT_ADMIN_GROUP_PERMISSIONS = ['GET', 'PUT', 'POST', 'DELETE']


def before_inserting_projects(items):
    """Strip unwanted properties, that will be assigned after creation. Also,
    verify permission to create a project (check quota, check role).

    :param items: List of project docs that have been inserted (normally one)
    """

    # Allow admin users to do whatever they want.
    if user_has_role('admin'):
        return

    for item in items:
        item.pop('url', None)


def override_is_private_field(project, original):
    """Override the 'is_private' property from the world permissions.

    :param project: the project, which will be updated
    """

    # No permissions, no access.
    if 'permissions' not in project:
        project['is_private'] = True
        return

    world_perms = project['permissions'].get('world', [])
    is_private = 'GET' not in world_perms
    project['is_private'] = is_private


def before_inserting_override_is_private_field(projects):
    for project in projects:
        override_is_private_field(project, None)


def before_edit_check_permissions(document, original):
    check_permissions('projects', original, request.method)


def before_delete_project(document):
    """Checks permissions before we allow deletion"""

    check_permissions('projects', document, request.method)


def protect_sensitive_fields(document, original):
    """When not logged in as admin, prevents update to certain fields."""

    # Allow admin users to do whatever they want.
    if user_has_role('admin'):
        return

    def revert(name):
        if name not in original:
            try:
                del document[name]
            except KeyError:
                pass
            return
        document[name] = original[name]

    revert('status')
    revert('category')
    revert('user')

    if 'url' in original:
        revert('url')


def after_inserting_projects(projects):
    """After inserting a project in the collection we do some processing such as:
    - apply the right permissions
    - define basic node types
    - optionally generate a url
    - initialize storage space

    :param projects: List of project docs that have been inserted (normally one)
    """

    users_collection = current_app.data.driver.db['users']
    for project in projects:
        owner_id = project.get('user', None)
        owner = users_collection.find_one(owner_id)
        after_inserting_project(project, owner)


def after_inserting_project(project, db_user):
    from pillar.auth import UserClass

    project_id = project['_id']
    user_id = db_user['_id']

    # Create a project-specific admin group (with name matching the project id)
    result, _, _, status = current_app.post_internal('groups', {'name': str(project_id)})
    if status != 201:
        log.error('Unable to create admin group for new project %s: %s',
                  project_id, result)
        return abort_with_error(status)

    admin_group_id = result['_id']
    log.debug('Created admin group %s for project %s', admin_group_id, project_id)

    # Assign the current user to the group
    db_user.setdefault('groups', []).append(admin_group_id)

    result, _, _, status = current_app.patch_internal('users', {'groups': db_user['groups']},
                                                      _id=user_id)
    if status != 200:
        log.error('Unable to add user %s as member of admin group %s for new project %s: %s',
                  user_id, admin_group_id, project_id, result)
        return abort_with_error(status)
    log.debug('Made user %s member of group %s', user_id, admin_group_id)

    # Assign the group to the project with admin rights
    owner_user = UserClass.construct('', db_user)
    is_admin = authorization.is_admin(owner_user)
    world_permissions = ['GET'] if is_admin else []
    permissions = {
        'world': world_permissions,
        'users': [],
        'groups': [
            {'group': admin_group_id,
             'methods': DEFAULT_ADMIN_GROUP_PERMISSIONS[:]},
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
        with_permissions(node_type_comment),
        with_permissions(node_type_texture),
        with_permissions(node_type_group_texture),
    ]

    # Allow admin users to use whatever url they want.
    if not is_admin or not project.get('url'):
        if project.get('category', '') == 'home':
            project['url'] = 'home'
        else:
            project['url'] = "p-{!s}".format(project_id)

    # Initialize storage using the default specified in STORAGE_BACKEND
    default_storage_backend(str(project_id))

    # Commit the changes directly to the MongoDB; a PUT is not allowed yet,
    # as the project doesn't have a valid permission structure.
    projects_collection = current_app.data.driver.db['projects']
    result = projects_collection.update_one({'_id': project_id},
                                            {'$set': remove_private_keys(project)})
    if result.matched_count != 1:
        log.error('Unable to update project %s: %s', project_id, result.raw_result)
        abort_with_error(500)


def before_returning_project_permissions(response):
    # Run validation process, since GET on nodes entry point is public
    check_permissions('projects', response, 'GET', append_allowed_methods=True)


def before_returning_project_resource_permissions(response):
    # Return only those projects the user has access to.
    allow = []
    for project in response['_items']:
        if authorization.has_permissions('projects', project,
                                         'GET', append_allowed_methods=True):
            allow.append(project)
        else:
            log.debug('User %s requested project %s, but has no access to it; filtered out.',
                      authentication.current_user_id(), project['_id'])

    response['_items'] = allow


def project_node_type_has_method(response):
    """Check for a specific request arg, and check generate the allowed_methods
    list for the required node_type.
    """

    node_type_name = request.args.get('node_type', '')

    # Proceed only node_type has been requested
    if not node_type_name:
        return

    # Look up the node type in the project document
    if not any(node_type.get('name') == node_type_name
               for node_type in response['node_types']):
        return abort(404)

    # Check permissions and append the allowed_methods to the node_type
    check_permissions('projects', response, 'GET', append_allowed_methods=True,
                      check_node_type=node_type_name)


def projects_node_type_has_method(response):
    for project in response['_items']:
        project_node_type_has_method(project)


