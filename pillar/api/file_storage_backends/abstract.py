import abc
import io
import logging
import typing

import pathlib
from bson import ObjectId

__all__ = ['Bucket', 'Blob', 'Path', 'FileType']

# Shorthand for the type of path we use.
Path = pathlib.PurePosixPath

# This is a mess: typing.IO keeps mypy-0.501 happy, but not in all cases,
# and io.FileIO keeps PyCharm-2017.1 happy.
FileType = typing.Union[typing.IO, io.FileIO]


class Bucket(metaclass=abc.ABCMeta):
    """Can be a GCS bucket or simply a project folder in Pillar

    :type name: string
    :param name: Name of the bucket. As a convention, we use the ID of
    the project to name the bucket.

    """

    # Mapping from backend name to Bucket class
    backends: typing.Dict[str, typing.Type['Bucket']] = {}

    backend_name: str = None  # define in subclass.

    def __init__(self, name: str) -> None:
        self.name = name

    def __init_subclass__(cls):
        assert cls.backend_name, '%s.backend_name must be non-empty string' % cls
        cls.backends[cls.backend_name] = cls

    def __repr__(self):
        return f'<{self.__class__.__name__} name={self.name!r}>'

    @classmethod
    def for_backend(cls, backend_name: str) -> typing.Type['Bucket']:
        """Returns the Bucket subclass for the given backend."""
        return cls.backends[backend_name]

    @abc.abstractmethod
    def blob(self, blob_name: str) -> 'Blob':
        """Factory constructor for blob object.

        :param blob_name: The path of the blob to be instantiated.
        """

    @abc.abstractmethod
    def get_blob(self, blob_name: str) -> typing.Optional['Blob']:
        """Get a blob object by name.

        If the blob exists return the object, otherwise None.
        """

    @abc.abstractmethod
    def copy_blob(self, blob: 'Blob', to_bucket: 'Bucket'):
        """Copies a blob from the current bucket to the other bucket.
        
        Implementations only need to support copying between buckets of the
        same storage backend.
        """

    @classmethod
    def copy_to_bucket(cls, blob_name, src_project_id: ObjectId, dest_project_id: ObjectId):
        """Copies a file from one bucket to the other."""

        src_storage = cls(str(src_project_id))
        dest_storage = cls(str(dest_project_id))

        blob = src_storage.get_blob(blob_name)
        src_storage.copy_blob(blob, dest_storage)


Bu = typing.TypeVar('Bu', bound=Bucket)


class Blob(metaclass=abc.ABCMeta):
    """A wrapper for file or blob objects."""

    def __init__(self, name: str, bucket: Bucket) -> None:
        self.name = name
        self.bucket = bucket
        self._size_in_bytes: typing.Optional[int] = None

        self.filename: str = None
        """Name of the file for the Content-Disposition header when downloading it."""

        self._log = logging.getLogger(f'{__name__}.Blob')

    def __repr__(self):
        return f'<{self.__class__.__name__} bucket={self.bucket.name!r} name={self.name!r}>'

    @property
    def size(self) -> typing.Optional[int]:
        """Size of the object, in bytes.

        :returns: The size of the blob or ``None`` if the property
                  is not set locally.
        """

        size = self._size_in_bytes
        if size is None:
            return None
        return int(size)

    @abc.abstractmethod
    def create_from_file(self, file_obj: FileType, *,
                         content_type: str,
                         file_size: int = -1):
        """Copies the file object to the storage.
        
        :param file_obj: The file object to send to storage.
        :param content_type: The content type of the file.
        :param file_size: The size of the file in bytes, or -1 if unknown
        """

    def upload_from_path(self, path: pathlib.Path, content_type: str):
        file_size = path.stat().st_size

        with path.open('rb') as infile:
            self.create_from_file(infile, content_type=content_type,
                                  file_size=file_size)

    @abc.abstractmethod
    def update_filename(self, filename: str):
        """Sets the filename which is used when downloading the file.
        
        Not all storage backends support this, and will use the on-disk filename instead.
        """

    @abc.abstractmethod
    def get_url(self, *, is_public: bool) -> str:
        """Returns the URL to access this blob.
        
        Note that this may involve API calls to generate a signed URL.
        """

    @abc.abstractmethod
    def make_public(self):
        """Makes the blob publicly available.
        
        Only performs an actual action on backends that support temporary links.
        """

    @abc.abstractmethod
    def exists(self) -> bool:
        """Returns True iff the file exists on the storage backend."""


Bl = typing.TypeVar('Bl', bound=Blob)
