"""Utility for managing storage backends and files."""

import logging
import os
import shutil

from flask import current_app

log = logging.getLogger(__name__)


class StorageBackend(object):
    """Can be a GCS bucket or simply a project folder in Pillar

    :type backend: string
    :param backend: Name of the storage backend (gcs, pillar, cdnsun).

    """

    def __init__(self, backend):
        self.backend = backend


class FileInStorage(object):
    """A wrapper for file or blob objects.

    :type backend: string
    :param backend: Name of the storage backend (gcs, pillar, cdnsun).

    """

    def __init__(self, backend):
        self.backend = backend
        self.path = None
        self.size = None


class PillarStorage(StorageBackend):
    def __init__(self, project_id):
        super(PillarStorage, self).__init__(backend='local')


class PillarStorageFile(FileInStorage):
    def __init__(self, project_id, internal_fname):
        super(PillarStorageFile, self).__init__(backend='local')

        self.size = None
        self.partial_path = os.path.join(project_id[:2], project_id,
                                         internal_fname[:2], internal_fname)
        self.path = os.path.join(
            current_app.config['STORAGE_DIR'], self.partial_path)

    def create_from_file(self, uploaded_file, file_size):
        # Ensure path exists before saving
        os.makedirs(os.path.dirname(self.path))

        with open(self.path, 'wb') as outfile:
            shutil.copyfileobj(uploaded_file, outfile)

        self.size = file_size
