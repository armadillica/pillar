import logging
import typing

import pathlib
from flask import current_app

from pillar.api.utils.imaging import generate_local_thumbnails

__all__ = ['LocalBucket', 'LocalBlob']

from .abstract import Bucket, Blob, FileType, Path


class LocalBucket(Bucket):
    backend_name = 'local'

    def __init__(self, name: str) -> None:
        super().__init__(name)

        self._log = logging.getLogger(f'{__name__}.LocalBucket')

        # For local storage, the name is actually a partial path, relative
        # to the local storage root.
        self.root = pathlib.Path(current_app.config['STORAGE_DIR'])
        self.bucket_path = pathlib.PurePosixPath(name[:2]) / name
        self.abspath = self.root / self.bucket_path

    def blob(self, blob_name: str) -> 'LocalBlob':
        return LocalBlob(name=blob_name, bucket=self)

    def get_blob(self, blob_name: str) -> typing.Optional['LocalBlob']:
        # TODO: Check if file exists, otherwise None
        return self.blob(blob_name)

    def copy_blob(self, blob: Blob, to_bucket: Bucket):
        """Copies a blob from the current bucket to the other bucket.
        
        Implementations only need to support copying between buckets of the
        same storage backend.
        """

        assert isinstance(blob, LocalBlob)
        assert isinstance(to_bucket, LocalBucket)

        self._log.info('Copying %s to bucket %s', blob, to_bucket)

        dest_blob = to_bucket.blob(blob.name)

        # TODO: implement content type handling for local storage.
        self._log.warning('Unable to set correct file content type for %s', dest_blob)

        with open(blob.abspath(), 'rb') as src_file:
            dest_blob.create_from_file(src_file, content_type='application/x-octet-stream')


class LocalBlob(Blob):
    """Blob representing a local file on the filesystem."""

    bucket: LocalBucket

    def __init__(self, name: str, bucket: LocalBucket) -> None:
        super().__init__(name, bucket)

        self._log = logging.getLogger(f'{__name__}.LocalBlob')
        self.partial_path = Path(name[:2]) / name

    def abspath(self) -> pathlib.Path:
        """Returns a concrete, absolute path to the local file."""

        return pathlib.Path(self.bucket.abspath / self.partial_path)

    def get_url(self, *, is_public: bool) -> str:
        from flask import url_for

        path = self.bucket.bucket_path / self.partial_path
        url = url_for('file_storage.index', file_name=str(path), _external=True,
                      _scheme=current_app.config['SCHEME'])
        return url

    def create_from_file(self, file_obj: FileType, *,
                         content_type: str,
                         file_size: int = -1):
        assert hasattr(file_obj, 'read')

        import shutil

        # Ensure path exists before saving
        my_path = self.abspath()
        my_path.parent.mkdir(exist_ok=True, parents=True)

        with my_path.open('wb') as outfile:
            shutil.copyfileobj(typing.cast(typing.IO, file_obj), outfile)

        self._size_in_bytes = file_size

    def update_filename(self, filename: str):
        # TODO: implement this for local storage.
        self._log.info('update_filename(%r) not supported', filename)

    def make_public(self):
        # No-op on this storage backend.
        pass

    def exists(self) -> bool:
        return self.abspath().exists()
