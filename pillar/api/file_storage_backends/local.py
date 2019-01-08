import logging
import pathlib
import typing

from flask import current_app

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
        self.bucket_path = pathlib.PurePosixPath(self.name[:2]) / self.name
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

        fpath = blob.abspath()
        if not fpath.exists():
            if not fpath.parent.exists():
                raise FileNotFoundError(f'File {fpath} does not exist, and neither does its parent,'
                                        f' unable to copy to {to_bucket}')
            raise FileNotFoundError(f'File {fpath} does not exist, unable to copy to {to_bucket}')

        with open(fpath, 'rb') as src_file:
            dest_blob.create_from_file(src_file, content_type='application/x-octet-stream')

    def rename_blob(self, blob: 'LocalBlob', new_name: str) -> 'LocalBlob':
        """Rename the blob, returning the new Blob."""

        assert isinstance(blob, LocalBlob)

        self._log.info('Renaming %s to %r', blob, new_name)
        new_blob = LocalBlob(new_name, self)

        old_path = blob.abspath()
        new_path = new_blob.abspath()
        new_path.parent.mkdir(parents=True, exist_ok=True)
        old_path.rename(new_path)

        return new_blob


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

    def update_filename(self, filename: str, *, is_attachment=True):
        # TODO: implement this for local storage.
        self._log.info('update_filename(%r) not supported', filename)

    def update_content_type(self, content_type: str, content_encoding: str = ''):
        self._log.info('update_content_type(%r, %r) not supported', content_type, content_encoding)

    def make_public(self):
        # No-op on this storage backend.
        pass

    def exists(self) -> bool:
        return self.abspath().exists()

    def touch(self):
        """Touch the file, creating parent directories if needed."""
        path = self.abspath()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
