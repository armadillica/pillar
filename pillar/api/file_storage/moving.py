"""Code for moving files between backends."""

import datetime
import logging
import os
import tempfile

from bson import ObjectId
import bson.tz_util
from flask import current_app
import requests
import requests.exceptions

from . import stream_to_gcs, generate_all_links, ensure_valid_link
import pillar.api.utils.gcs

__all__ = ['PrerequisiteNotMetError', 'change_file_storage_backend']

log = logging.getLogger(__name__)


class PrerequisiteNotMetError(RuntimeError):
    """Raised when a file cannot be moved due to unmet prerequisites."""


def change_file_storage_backend(file_id, dest_backend):
    """Given a file document, move it to the specified backend (if not already
    there) and update the document to reflect that.
    Files on the original backend are not deleted automatically.
    """

    dest_backend = unicode(dest_backend)
    file_id = ObjectId(file_id)

    # Fetch file document
    files_collection = current_app.data.driver.db['files']
    f = files_collection.find_one(file_id)
    if f is None:
        raise ValueError('File with _id: {} not found'.format(file_id))

    # Check that new backend differs from current one
    if dest_backend == f['backend']:
        raise PrerequisiteNotMetError('Destination backend ({}) matches the current backend, we '
                                      'are not moving the file'.format(dest_backend))

    # TODO Check that new backend is allowed (make conf var)

    # Check that the file has a project; without project, we don't know
    # which bucket to store the file into.
    try:
        project_id = f['project']
    except KeyError:
        raise PrerequisiteNotMetError('File document does not have a project')

    # Ensure that all links are up to date before we even attempt a download.
    ensure_valid_link(f)

    # Upload file and variations to the new backend
    variations = f.get('variations', ())

    try:
        copy_file_to_backend(file_id, project_id, f, f['backend'], dest_backend)
    except requests.exceptions.HTTPError as ex:
        # allow the main file to be removed from storage.
        if ex.response.status_code not in {404, 410}:
            raise
        if not variations:
            raise PrerequisiteNotMetError('Main file ({link}) does not exist on server, '
                                          'and no variations exist either'.format(**f))
        log.warning('Main file %s does not exist; skipping main and visiting variations', f['link'])

    for var in variations:
        copy_file_to_backend(file_id, project_id, var, f['backend'], dest_backend)

    # Generate new links for the file & all variations. This also saves
    # the new backend we set here.
    f['backend'] = dest_backend
    now = datetime.datetime.now(tz=bson.tz_util.utc)
    generate_all_links(f, now)


def copy_file_to_backend(file_id, project_id, file_or_var, src_backend, dest_backend):
    # Filenames on GCS do not contain paths, by our convention
    internal_fname = os.path.basename(file_or_var['file_path'])
    file_or_var['file_path'] = internal_fname

    # If the file is not local already, fetch it
    if src_backend == 'pillar':
        local_finfo = fetch_file_from_local(file_or_var)
    else:
        local_finfo = fetch_file_from_link(file_or_var['link'])

    # Upload to GCS
    if dest_backend != 'gcs':
        raise ValueError('Only dest_backend="gcs" is supported now.')

    if current_app.config['TESTING']:
        log.warning('Skipping actual upload to GCS due to TESTING')
    else:
        # TODO check for name collisions
        stream_to_gcs(file_id, local_finfo['file_size'],
                      internal_fname=internal_fname,
                      project_id=str(project_id),
                      stream_for_gcs=local_finfo['local_file'],
                      content_type=local_finfo['content_type'])

    # No longer needed, so it can be closed & dispersed of.
    local_finfo['local_file'].close()


def fetch_file_from_link(link):
    """Utility to download a file from a remote location and return it with
    additional info (for upload to a different storage backend).
    """

    log.info('Downloading %s', link)
    r = requests.get(link, stream=True)
    r.raise_for_status()

    local_file = tempfile.NamedTemporaryFile(dir=current_app.config['STORAGE_DIR'])
    log.info('Downloading to %s', local_file.name)

    for chunk in r.iter_content(chunk_size=1024):
        if chunk:
            local_file.write(chunk)
    local_file.seek(0)

    file_dict = {
        'file_size': os.fstat(local_file.fileno()).st_size,
        'content_type': r.headers.get('content-type', 'application/octet-stream'),
        'local_file': local_file
    }
    return file_dict


def fetch_file_from_local(file_doc):
    """Mimicks fetch_file_from_link(), but just returns the local file.

    :param file_doc: dict with 'link' key pointing to a path in STORAGE_DIR, and
        'content_type' key.
    :type file_doc: dict
    :rtype: dict        self._log.info('Moving file %s to project %s', file_id, dest_proj['_id'])

    """

    local_file = open(os.path.join(current_app.config['STORAGE_DIR'], file_doc['file_path']), 'rb')
    local_finfo = {
        'file_size': os.fstat(local_file.fileno()).st_size,
        'content_type': file_doc['content_type'],
        'local_file': local_file
    }
    return local_finfo


def gcs_move_to_bucket(file_id, dest_project_id, skip_gcs=False):
    """Moves a file from its own bucket to the new project_id bucket."""

    files_coll = current_app.db()['files']

    f = files_coll.find_one(file_id)
    if f is None:
        raise ValueError('File with _id: {} not found'.format(file_id))

    # Check that new backend differs from current one
    if f['backend'] != 'gcs':
        raise ValueError('Only Google Cloud Storage is supported for now.')

    # Move file and variations to the new bucket.
    if skip_gcs:
        log.warning('NOT ACTUALLY MOVING file %s on GCS, just updating MongoDB', file_id)
    else:
        src_project = f['project']
        pillar.api.utils.gcs.copy_to_bucket(f['file_path'], src_project, dest_project_id)
        for var in f.get('variations', []):
            pillar.api.utils.gcs.copy_to_bucket(var['file_path'], src_project, dest_project_id)

    # Update the file document after moving was successful.
    log.info('Switching file %s to project %s', file_id, dest_project_id)
    update_result = files_coll.update_one({'_id': file_id},
                                          {'$set': {'project': dest_project_id}})
    if update_result.matched_count != 1:
        raise RuntimeError(
            'Unable to update file %s in MongoDB: matched_count=%i; modified_count=%i' % (
                file_id, update_result.matched_count, update_result.modified_count))

    log.info('Switching file %s: matched_count=%i; modified_count=%i',
             file_id, update_result.matched_count, update_result.modified_count)

    # Regenerate the links for this file
    f['project'] = dest_project_id
    generate_all_links(f, now=datetime.datetime.now(tz=bson.tz_util.utc))
