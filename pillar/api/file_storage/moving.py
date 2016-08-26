"""Code for moving files between backends."""

__all__ = ['PrerequisiteNotMetError', 'change_file_storage_backend']


class PrerequisiteNotMetError(RuntimeError):
    """Raised when a file cannot be moved due to unmet prerequisites."""


def change_file_storage_backend(file_id, dest_backend):
    """Given a file document, move it to the specified backend (if not already
    there) and update the document to reflect that.
    Files on the original backend are not deleted automatically.
    """

    # Fetch file document
    files_collection = current_app.data.driver.db['files']
    f = files_collection.find_one(ObjectId(file_id))
    if f is None:
        raise ValueError('File with _id: {} not found'.format(file_id))

    # Check that new backend differs from current one
    if dest_backend == f['backend']:
        log.warning('Destination backend ({}) matches the current backend, we '
                    'are not moving the file'.format(dest_backend))
        return

    # TODO Check that new backend is allowed (make conf var)

    # Check that the file has a project; without project, we don't know
    # which bucket to store the file into.
    if 'project' not in f:
        raise PrerequisiteNotMetError('File document {} does not have a project'.format(file_id))

    # Upload file (TODO: and variations) to the new backend
    move_file_to_backend(f, dest_backend)

    # Update document to reflect the changes


def move_file_to_backend(file_doc, dest_backend):
    # If the file is not local already, fetch it
    if file_doc['backend'] != 'local':
        # TODO ensure that file['link'] is up to date
        local_file = fetch_file_from_link(file_doc['link'])

    # Upload to GCS
    if dest_backend == 'gcs':
        # Filenames on GCS do not contain paths, by our convention
        internal_fname = os.path.basename(file_doc['file_path'])
        # TODO check for name collisions
        stream_to_gcs(file_doc['_id'], local_file['file_size'],
                      internal_fname=internal_fname,
                      project_id=str(file_doc['project']),
                      stream_for_gcs=local_file['local_file'],
                      content_type=local_file['content_type'])


def fetch_file_from_link(link):
    """Utility to download a file from a remote location and return it with
    additional info (for upload to a different storage backend).
    """

    r = requests.get(link, stream=True)
    r.raise_for_status()
    
    # If the file is not found we will use one from the variations. Original
    # files might not exists because they were too large to keep.
    if r.status_code == 404:
        pass
    local_file = tempfile.NamedTemporaryFile(
        dir=current_app.config['STORAGE_DIR'])
    with open(local_file, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
    file_dict = {
        'file_size': os.fstat(local_file.fileno()).st_size,
        'content_type': r.headers['content-type'],
        'local_file': local_file
    }
    return file_dict
