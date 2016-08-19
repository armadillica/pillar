import logging

from bson import ObjectId
from flask import current_app
from werkzeug import exceptions as wz_exceptions
from werkzeug.exceptions import abort

log = logging.getLogger(__name__)


def project_total_file_size(project_id):
    """Returns the total number of bytes used by files of this project."""

    files = current_app.data.driver.db['files']
    file_size_used = files.aggregate([
        {'$match': {'project': ObjectId(project_id)}},
        {'$project': {'length_aggregate_in_bytes': 1}},
        {'$group': {'_id': None,
                    'all_files': {'$sum': '$length_aggregate_in_bytes'}}}
    ])

    # The aggregate function returns a cursor, not a document.
    try:
        return next(file_size_used)['all_files']
    except StopIteration:
        # No files used at all.
        return 0


def get_admin_group(project):
    """Returns the admin group for the project."""

    groups_collection = current_app.data.driver.db['groups']

    # TODO: search through all groups to find the one with the project ID as its name.
    admin_group_id = ObjectId(project['permissions']['groups'][0]['group'])
    group = groups_collection.find_one({'_id': admin_group_id})

    if group is None:
        raise ValueError('Unable to handle project without admin group.')

    if group['name'] != str(project['_id']):
        return abort_with_error(403)

    return group


def abort_with_error(status):
    """Aborts with the given status, or 500 if the status doesn't indicate an error.

    If the status is < 400, status 500 is used instead.
    """

    abort(status if status // 100 >= 4 else 500)
    raise wz_exceptions.InternalServerError('abort() should have aborted!')


def create_new_project(project_name, user_id, overrides):
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

    result, _, _, status = current_app.post_internal('projects', project)
    if status != 201:
        log.error('Unable to create project "%s": %s', project_name, result)
        return abort_with_error(status)
    project.update(result)

    # Now re-fetch the project, as both the initial document and the returned
    # result do not contain the same etag as the database. This also updates
    # other fields set by hooks.
    document = current_app.data.driver.db['projects'].find_one(project['_id'])
    project.update(document)

    log.info('Created project %s for user %s', project['_id'], user_id)

    return project
