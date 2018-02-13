"""Project patching support."""

import logging

import flask
from flask import Blueprint, request
import werkzeug.exceptions as wz_exceptions

from pillar import current_app
from pillar.auth import current_user
from pillar.api.utils import random_etag, str2id, utcnow
from pillar.api.utils import authorization

log = logging.getLogger(__name__)
blueprint = Blueprint('projects.patch', __name__)


@blueprint.route('/<project_id>', methods=['PATCH'])
@authorization.require_login()
def patch_project(project_id: str):
    """Undelete a project.

    This is done via a custom PATCH due to the lack of transactions of MongoDB;
    we cannot undelete both project-referenced files and file-referenced
    projects in one atomic operation.
    """

    # Parse the request
    pid = str2id(project_id)
    patch = request.get_json()
    if not patch:
        raise wz_exceptions.BadRequest('Expected JSON body')

    log.debug('User %s wants to PATCH project %s: %s', current_user, pid, patch)

    # 'undelete' is the only operation we support now, so no fancy handler registration.
    op = patch.get('op', '')
    if op != 'undelete':
        log.warning('User %s sent unsupported PATCH op %r to project %s: %s',
                    current_user, op, pid, patch)
        raise wz_exceptions.BadRequest(f'unsupported operation {op!r}')

    # Get the project to find the user's permissions.
    proj_coll = current_app.db('projects')
    proj = proj_coll.find_one({'_id': pid})
    if not proj:
        raise wz_exceptions.NotFound(f'project {pid} not found')
    allowed = authorization.compute_allowed_methods('projects', proj)
    if 'PUT' not in allowed:
        log.warning('User %s tried to undelete project %s but only has permissions %r',
                    current_user, pid, allowed)
        raise wz_exceptions.Forbidden(f'no PUT access to project {pid}')

    if not proj.get('_deleted', False):
        raise wz_exceptions.BadRequest(f'project {pid} was not deleted, unable to undelete')

    # Undelete the files. We cannot do this via Eve, as it doesn't support
    # PATCHing collections, so direct MongoDB modification is used to set
    # _deleted=False and provide new _etag and _updated values.
    new_etag = random_etag()

    log.debug('undeleting files before undeleting project %s', pid)
    files_coll = current_app.db('files')
    update_result = files_coll.update_many(
        {'project': pid},
        {'$set': {'_deleted': False,
                  '_etag': new_etag,
                  '_updated': utcnow()}})
    log.info('undeleted %d of %d file documents of project %s',
             update_result.modified_count, update_result.matched_count, pid)

    log.info('undeleting project %s on behalf of user %s', pid, current_user)
    update_result = proj_coll.update_one({'_id': pid},
                                         {'$set': {'_deleted': False}})
    log.info('undeleted %d project document %s', update_result.modified_count, pid)

    resp = flask.Response('', status=204)
    resp.location = flask.url_for('projects.view', project_url=proj['url'])
    return resp


def setup_app(app):
    # This needs to be on the same URL prefix as Eve uses for the collection,
    # and not /p as used for the other Projects API calls.
    app.register_api_blueprint(blueprint, url_prefix='/projects')
