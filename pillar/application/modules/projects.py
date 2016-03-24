import logging
from flask import g
from flask import abort
from eve.methods.put import put_internal
from eve.methods.post import post_internal
from application import app
from application.utils import remove_private_keys
from application.utils.gcs import GoogleCloudStorageBucket
from manage.node_types.asset import node_type_asset
from manage.node_types.group import node_type_group
from manage.node_types.page import node_type_page
from manage.node_types.comment import node_type_comment

log = logging.getLogger(__name__)


def before_inserting_projects(items):
    """Strip unwanted properties, that will be assigned after creation. Also,
    verify permission to create a project (check quota, check role).

    :param items: List of project docs that have been inserted (normally one)
    """
    for item in items:
        item.pop('url', None)


def after_inserting_projects(items):
    """After inserting a project in the collection we do some processing such as:
    - apply the right permissions
    - define basic node types
    - optionally generate a url
    - initialize storage space

    :param items: List of project docs that have been inserted (normally one)
    """
    current_user = g.get('current_user', None)
    users_collection = app.data.driver.db['users']
    user = users_collection.find_one({'_id': current_user['user_id']})

    for item in items:
        # Create a project specific group (with name matching the project id)
        project_group = dict(name=str(item['_id']))
        group = post_internal('groups', project_group)
        # If Group creation failed, stop
        # TODO: undo project creation
        if group[3] != 201:
            abort(group[3])
        else:
            group = group[0]
        # Assign the current user to the group
        if 'groups' in user:
            user['groups'].append(group['_id'])
        else:
            user['groups'] = [group['_id']]
        put_internal('users', remove_private_keys(user), _id=user['_id'])
        # Assign the group to the project with admin rights
        permissions = dict(
            world=['GET'],
            users=[],
            groups=[
                dict(group=group['_id'],
                     methods=['GET', 'PUT', 'POST'])
            ]
        )
        # Assign permissions to the project itself, as well as to the node_types
        item['permissions'] = permissions
        node_type_asset['permissions'] = permissions
        node_type_group['permissions'] = permissions
        node_type_page['permissions'] = permissions
        node_type_comment['permissions'] = permissions
        # Assign the basic 'group', 'asset' and 'page' node_types
        item['node_types'] = [
            node_type_group,
            node_type_asset,
            node_type_page,
            node_type_comment]
        # TODO: Depending on user role or status, assign the url attribute
        # Initialize storage page (defaults to GCS)
        gcs_storage = GoogleCloudStorageBucket(str(item['_id']))
        if gcs_storage.bucket.exists():
            log.debug("Created CGS bucket {0}".format(item['_id']))
        # Assign a url based on the project id
        item['url'] = "p-{}".format(item['_id'])
        # Commit the changes
        put_internal('projects', remove_private_keys(item), _id=item['_id'])
