"""Utility for managing storage backends and files."""

import abc
import logging
import os
import shutil

from flask import current_app

log = logging.getLogger(__name__)

# Mapping from backend name to backend class
backends = {}


def register_backend(backend_name):
    def wrapper(cls):
        assert backend_name not in backends
        backends[backend_name] = cls
        return cls

    return wrapper


class StorageBackend(object):
    """Can be a GCS bucket or simply a project folder in Pillar

    :type backend: string
    :param backend: Name of the storage backend (gcs, pillar, cdnsun).

    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, backend):
        self.backend = backend

    @abc.abstractmethod
    def upload_file(self, param1, param2, param3):
        """docstuff"""
        pass


class FileInStorage(object):
    """A wrapper for file or blob objects.

    :type backend: string
    :param backend: Name of the storage backend (gcs, pillar, cdnsun).

    """

    def __init__(self, backend):
        self.backend = backend
        self.path = None
        self.size = None


@register_backend('local')
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


def default_storage_backend():
    from flask import current_app

    backend_cls = backends[current_app.config['STORAGE_BACKEND']]
    return backend_cls()
