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


class Bucket(object):
    """Can be a GCS bucket or simply a project folder in Pillar

    :type name: string
    :param name: Name of the bucket. As a convention, we use the ID of
    the project to name the bucket.

    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, name):
        self.name = name

    @abc.abstractmethod
    def blob(self, blob_name):
        """Factory constructor for blob object.

        :type blob_name: string
        :param blob_name: The name of the blob to be instantiated.
        """
        return Blob(name=blob_name, bucket=self)

    @abc.abstractmethod
    def get_blob(self, blob_name):
        """Get a blob object by name.

        If the blob exists return the object, otherwise None.
        """
        pass


class Blob(object):
    """A wrapper for file or blob objects.

    :type name: string
    :param name: Name of the blob.

    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, name, bucket):
        self.name = name
        self.bucket = bucket
        self._size_in_bytes = None

    @property
    def size(self):
        """Size of the object, in bytes.

        :rtype: integer or ``NoneType``
        :returns: The size of the blob or ``None`` if the property
                  is not set locally.
        """
        size = self._size_in_bytes
        if size is not None:
            return int(size)
        return self._size_in_bytes

    @abc.abstractmethod
    def create_from_file(self, uploaded_file, file_size):
        pass


@register_backend('local')
class LocalBucket(Bucket):
    def __init__(self, name):
        super(LocalBucket, self).__init__(name=name)

    def blob(self, blob_name):
        return LocalBlob(name=blob_name, bucket=self)

    def get_blob(self, blob_name):
        # Check if file exists, otherwise None
        return None


class LocalBlob(Blob):
    def __init__(self, name, bucket):
        super(LocalBlob, self).__init__(name=name, bucket=bucket)

        bucket_name = bucket.name
        self.partial_path = os.path.join(bucket_name[:2], bucket_name,
                                         name[:2], name)
        self.path = os.path.join(
            current_app.config['STORAGE_DIR'], self.partial_path)

    def create_from_file(self, uploaded_file, file_size):
        # Ensure path exists before saving
        os.makedirs(os.path.dirname(self.path))

        with open(self.path, 'wb') as outfile:
            shutil.copyfileobj(uploaded_file, outfile)

        self._size_in_bytes = file_size


def default_storage_backend(name):
    from flask import current_app

    backend_cls = backends[current_app.config['STORAGE_BACKEND']]
    return backend_cls(name)
