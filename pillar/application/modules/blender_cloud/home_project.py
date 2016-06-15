import logging

from bson import ObjectId
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
HOME_PROJECT_USERS = {u'subscriber', u'demo'}


def create_home_project(user_id):
    """Creates a home project for the given user."""

    log.info('Creating home project for user %s', user_id)
    project = projects.create_new_project(project_name='Home',
                                          user_id=ObjectId(user_id),
                                          overrides={'category': 'home'})

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
    from manage_extra.node_types.text import node_type_text

    project['node_types'] = [
        node_type_group,
        node_type_asset,
        node_type_text,
    ]

    result, _, _, status = put_internal('projects', utils.remove_private_keys(project),
                                        _id=project['_id'])
    if status != 200:
        log.error('Unable to update home project %s for user %s: %s',
                  project['_id'], user_id, result)
        raise wz_exceptions.InternalServerError('Unable to update home project')
    project.update(result)

    return project


@blueprint.route('/home-project')
@authorization.require_login(require_roles={u'subscriber', u'demo'})
def home_project():
    """Fetches the home project, creating it if necessary.

    Eve projections are supported, but at least the following fields must be present:
        'permissions', 'category', 'user'
    """
    user_id = g.current_user['user_id']
    roles = g.current_user.get('roles', ())

    log.debug('Possibly creating home project for user %s with roles %s', user_id, roles)
    if not HOME_PROJECT_USERS.intersection(roles):
        log.debug('User %s is not a subscriber, not creating home project.', user_id)
        return 'No home project', 404

    # Create the home project before we do the Eve query. This costs an extra round-trip
    # to the database, but makes it easier to do projections correctly.
    if not has_home_project(user_id):
        create_home_project(user_id)

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
    return proj_coll.count({'user': user_id, 'category': 'home'}) > 0


def setup_app(app, url_prefix):
    app.register_blueprint(blueprint, url_prefix=url_prefix)
