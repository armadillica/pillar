import copy
import logging

from bson import ObjectId
from eve.methods.post import post_internal
from eve.methods.put import put_internal
from eve.methods.get import get
from flask import Blueprint, g, current_app, request
from werkzeug import exceptions as wz_exceptions

from application.modules import projects
from application import utils
from application.utils import authentication, authorization

blueprint = Blueprint('blender_cloud.home_project', __name__)
log = logging.getLogger(__name__)

# Users with any of these roles will get a home project.
HOME_PROJECT_USERS = set()

# Users with any of these roles will get full write access to their home project.
HOME_PROJECT_WRITABLE_USERS = {u'subscriber', u'demo'}
SYNC_GROUP_NODE_NAME = u'Blender Sync'
SYNC_GROUP_NODE_DESC = 'The [Blender Cloud Addon](https://cloud.blender.org/services' \
                       '#blender-addon) will synchronize your Blender settings here.'


def create_blender_sync_node(project_id, admin_group_id, user_id):
    """Creates a node for Blender Sync, with explicit write access for the admin group.

    Writes the node to the database.

    :param project_id: ID of the home project
    :type project_id: ObjectId
    :param admin_group_id: ID of the admin group of the project. This group will
        receive write access to the node.
    :type admin_group_id: ObjectId
    :param user_id: ID of the owner of the node.
    :type user_id: ObjectId

    :returns: The created node.
    :rtype: dict
    """

    log.debug('Creating sync node for project %s, user %s', project_id, user_id)

    node = {
        'project': ObjectId(project_id),
        'node_type': 'group',
        'name': SYNC_GROUP_NODE_NAME,
        'user': ObjectId(user_id),
        'description': SYNC_GROUP_NODE_DESC,
        'properties': {'status': 'published'},
        'permissions': {
            'users': [],
            'groups': [
                {'group': ObjectId(admin_group_id),
                 'methods': ['GET', 'PUT', 'POST', 'DELETE']}
            ],
            'world': [],
        }
    }

    r, _, _, status = post_internal('nodes', node)
    if status != 201:
        log.warning('Unable to create Blender Sync node for home project %s: %s',
                    project_id, r)
        raise wz_exceptions.InternalServerError('Unable to create Blender Sync node')

    node.update(r)
    return node


def create_home_project(user_id, write_access):
    """Creates a home project for the given user.

    :param user_id: the user ID of the owner
    :param write_access: whether the user has full write access to the home project.
    :type write_access: bool
    """

    log.info('Creating home project for user %s', user_id)
    overrides = {
        'category': 'home',
        'summary': 'This is your home project. Pastebin and Blender settings sync in one!',
        'description': '# Your home project\n\n'
                       'This is your home project. It has functionality to act '
                       'as a pastebin for text, images and other assets, and '
                       'allows synchronisation of your Blender settings.'
    }

    # Maybe the user has a deleted home project.
    proj_coll = current_app.data.driver.db['projects']
    deleted_proj = proj_coll.find_one({'user': user_id, 'category': 'home', '_deleted': True})
    if deleted_proj:
        log.info('User %s has a deleted project %s, restoring', user_id, deleted_proj['_id'])
        project = deleted_proj
    else:
        log.debug('User %s does not have a deleted project', user_id)
        project = projects.create_new_project(project_name='Home',
                                              user_id=ObjectId(user_id),
                                              overrides=overrides)

    # Re-validate the authentication token, so that the put_internal call sees the
    # new group created for the project.
    authentication.validate_token()

    # There are a few things in the on_insert_projects hook we need to adjust.

    # Ensure that the project is private, even for admins.
    project['permissions']['world'] = []

    # Set up the correct node types. No need to set permissions for them,
    # as the inherited project permissions are fine.
    from manage_extra.node_types.group import node_type_group
    from manage_extra.node_types.asset import node_type_asset
    # from manage_extra.node_types.text import node_type_text
    from manage_extra.node_types.comment import node_type_comment

    if not write_access:
        # Take away write access from the admin group, and grant it to
        # certain node types.
        project['permissions']['groups'][0]['methods'] = ['GET']

    project['node_types'] = [
        node_type_group,
        node_type_asset,
        # node_type_text,
        node_type_comment,
    ]

    result, _, _, status = put_internal('projects', utils.remove_private_keys(project),
                                        _id=project['_id'])
    if status != 200:
        log.error('Unable to update home project %s for user %s: %s',
                  project['_id'], user_id, result)
        raise wz_exceptions.InternalServerError('Unable to update home project')
    project.update(result)

    # Create the Blender Sync node, with explicit write permissions on the node itself.
    create_blender_sync_node(project['_id'],
                             project['permissions']['groups'][0]['group'],
                             user_id)

    return project


@blueprint.route('/home-project')
@authorization.ab_testing(require_roles={u'homeproject'})
@authorization.require_login()
def home_project():
    """Fetches the home project, creating it if necessary.

    Eve projections are supported, but at least the following fields must be present:
        'permissions', 'category', 'user'
    """
    user_id = g.current_user['user_id']
    roles = g.current_user.get('roles', ())

    log.debug('Possibly creating home project for user %s with roles %s', user_id, roles)
    if HOME_PROJECT_USERS and not HOME_PROJECT_USERS.intersection(roles):
        log.debug('User %s is not a subscriber, not creating home project.', user_id)
        return 'No home project', 404

    # Create the home project before we do the Eve query. This costs an extra round-trip
    # to the database, but makes it easier to do projections correctly.
    if not has_home_project(user_id):
        write_access = bool(not HOME_PROJECT_WRITABLE_USERS or
                            HOME_PROJECT_WRITABLE_USERS.intersection(roles))
        create_home_project(user_id, write_access)

    resp, _, _, status, _ = get('projects', category=u'home', user=user_id)
    if status != 200:
        return utils.jsonify(resp), status

    if resp['_items']:
        project = resp['_items'][0]
    else:
        log.warning('Home project for user %s not found, while we just created it! Could be '
                    'due to projections and other arguments on the query string: %s',
                    user_id, request.query_string)
        return 'No home project', 404

    return utils.jsonify(project), status


def has_home_project(user_id):
    """Returns True iff the user has a home project."""

    proj_coll = current_app.data.driver.db['projects']
    return proj_coll.count({'user': user_id, 'category': 'home', '_deleted': False}) > 0


def is_home_project(project_id, user_id):
    """Returns True iff the given project exists and is the user's home project."""

    proj_coll = current_app.data.driver.db['projects']
    return proj_coll.count({'_id': project_id,
                            'user': user_id,
                            'category': 'home',
                            '_deleted': False}) > 0


def check_home_project_nodes_permissions(nodes):
    for node in nodes:
        check_home_project_node_permissions(node)


def check_home_project_node_permissions(node):
    """Grants POST access to the node when the user has POST access on its parent."""

    user_id = authentication.current_user_id()
    if not user_id:
        log.debug('check_home_project_node_permissions: user not logged in.')
        return

    parent_id = node.get('parent')
    if not parent_id:
        log.debug('check_home_project_node_permissions: not checking for top-level node.')
        return

    project_id = node.get('project')
    if not project_id:
        log.debug('check_home_project_node_permissions: ignoring node without project ID')
        return

    project_id = ObjectId(project_id)
    if not is_home_project(project_id, user_id):
        log.debug('check_home_project_node_permissions: node not part of home project.')
        return

    # Get the parent node for permission checking.
    parent_id = ObjectId(parent_id)
    nodes_coll = current_app.data.driver.db['nodes']
    parent_node = nodes_coll.find_one(parent_id,
                                      projection={'permissions': 1,
                                                  'project': 1,
                                                  'node_type': 1})
    if parent_node['project'] != project_id:
        log.warning('check_home_project_node_permissions: User %s is trying to reference '
                    'parent node %s from different project %s, expected project %s.',
                    user_id, parent_id, parent_node['project'], project_id)
        raise wz_exceptions.BadRequest('Trying to create cross-project links.')

    has_access = authorization.has_permissions('nodes', parent_node, 'POST')
    if not has_access:
        log.debug('check_home_project_node_permissions: No POST access to parent node %s, '
                  'ignoring.', parent_id)
        return

    # Grant access!
    log.debug('check_home_project_node_permissions: POST access at parent node %s, '
              'so granting POST access to new child node.', parent_id)

    # Make sure the permissions of the parent node are copied to this node.
    node['permissions'] = copy.deepcopy(parent_node['permissions'])


def setup_app(app, url_prefix):
    app.register_blueprint(blueprint, url_prefix=url_prefix)

    app.on_insert_nodes += check_home_project_nodes_permissions
