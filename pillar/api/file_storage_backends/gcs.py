import os
import datetime
import logging
import typing

from bson import ObjectId
from gcloud.storage.client import Client
import gcloud.storage.blob
import gcloud.exceptions as gcloud_exc
from flask import current_app, g
from werkzeug.local import LocalProxy

from .abstract import Bucket, Blob, FileType

log = logging.getLogger(__name__)


def get_client() -> Client:
    """Stores the GCS client on the global Flask object.

    The GCS client is not user-specific anyway.
    """

    _gcs = getattr(g, '_gcs_client', None)
    if _gcs is None:
        _gcs = g._gcs_client = Client()
    return _gcs


# This hides the specifics of how/where we store the GCS client,
# and allows the rest of the code to use 'gcs' as a simple variable
# that does the right thing.
gcs: Client = LocalProxy(get_client)


class GoogleCloudStorageBucket(Bucket):
    """Cloud Storage bucket interface. We create a bucket for every project. In
    the bucket we create first level subdirs as follows:
    - '_' (will contain hashed assets, and stays on top of default listing)
    - 'svn' (svn checkout mirror)
    - 'shared' (any additional folder of static folder that is accessed via a
      node of 'storage' node_type)

    :type bucket_name: string
    :param bucket_name: Name of the bucket.

    :type subdir: string
    :param subdir: The local entry point to browse the bucket.

    """

    backend_name = 'gcs'

    def __init__(self, name: str, subdir='_/') -> None:
        super().__init__(name=name)

        self._log = logging.getLogger(f'{__name__}.GoogleCloudStorageBucket')

        try:
            self._gcs_bucket = gcs.get_bucket(name)
        except gcloud_exc.NotFound:
            self._gcs_bucket = gcs.bucket(name)
            # Hardcode the bucket location to EU
            self._gcs_bucket.location = 'EU'
            # Optionally enable CORS from * (currently only used for vrview)
            # self.gcs_bucket.cors = [
            #     {
            #       "origin": ["*"],
            #       "responseHeader": ["Content-Type"],
            #       "method": ["GET", "HEAD", "DELETE"],
            #       "maxAgeSeconds": 3600
            #     }
            # ]
            self._gcs_bucket.create()
            log.info('Created GCS instance for project %s', name)

        self.subdir = subdir

    def blob(self, blob_name: str) -> 'GoogleCloudStorageBlob':
        return GoogleCloudStorageBlob(name=blob_name, bucket=self)

    def get_blob(self, internal_fname: str) -> typing.Optional['GoogleCloudStorageBlob']:
        blob = self.blob(internal_fname)
        if not blob.gblob.exists():
            return None
        return blob

    def _gcs_get(self, path: str, *, chunk_size=None) -> gcloud.storage.Blob:
        """Get selected file info if the path matches.

        :param path: The path to the file, relative to the bucket's subdir.
        """
        path = os.path.join(self.subdir, path)
        blob = self._gcs_bucket.blob(path, chunk_size=chunk_size)
        return blob

    def _gcs_post(self, full_path, *, path=None) -> typing.Optional[gcloud.storage.Blob]:
        """Create new blob and upload data to it.
        """
        path = path if path else os.path.join(self.subdir, os.path.basename(full_path))
        gblob = self._gcs_bucket.blob(path)
        if gblob.exists():
            self._log.error(f'Trying to upload to {path}, but that blob already exists. '
                            f'Not uploading.')
            return None

        gblob.upload_from_filename(full_path)
        return gblob
        # return self.blob_to_dict(blob) # Has issues with threading

    def delete_blob(self, path: str) -> bool:
        """Deletes the blob (when removing an asset or replacing a preview)"""

        # We want to get the actual blob to delete
        gblob = self._gcs_get(path)
        try:
            gblob.delete()
            return True
        except gcloud_exc.NotFound:
            return False

    def copy_blob(self, blob: Blob, to_bucket: Bucket):
        """Copies the given blob from this bucket to the other bucket.

        Returns the new blob.
        """

        assert isinstance(blob, GoogleCloudStorageBlob)
        assert isinstance(to_bucket, GoogleCloudStorageBucket)

        self._log.info('Copying %s to bucket %s', blob, to_bucket)

        return self._gcs_bucket.copy_blob(blob.gblob, to_bucket._gcs_bucket)

    def rename_blob(self, blob: 'GoogleCloudStorageBlob', new_name: str) \
            -> 'GoogleCloudStorageBlob':
        """Rename the blob, returning the new Blob."""

        assert isinstance(blob, GoogleCloudStorageBlob)

        new_name = os.path.join(self.subdir, new_name)

        self._log.info('Renaming %s to %r', blob, new_name)
        new_gblob = self._gcs_bucket.rename_blob(blob.gblob, new_name)
        return GoogleCloudStorageBlob(new_gblob.name, self, gblob=new_gblob)


class GoogleCloudStorageBlob(Blob):
    """GCS blob interface."""

    def __init__(self, name: str, bucket: GoogleCloudStorageBucket,
                 *, gblob: gcloud.storage.blob.Blob=None) -> None:
        super().__init__(name, bucket)

        self._log = logging.getLogger(f'{__name__}.GoogleCloudStorageBlob')
        self.gblob = gblob or bucket._gcs_get(name, chunk_size=256 * 1024 * 2)

    def create_from_file(self, file_obj: FileType, *,
                         content_type: str,
                         file_size: int = -1) -> None:
        from gcloud.streaming import transfer

        self._log.debug('Streaming file to GCS bucket %r, size=%i', self, file_size)

        # Files larger than this many bytes will be streamed directly from disk,
        # smaller ones will be read into memory and then uploaded.
        transfer.RESUMABLE_UPLOAD_THRESHOLD = 102400
        self.gblob.upload_from_file(file_obj,
                                    size=file_size,
                                    content_type=content_type)

        # Reload the blob to get the file size according to Google.
        self.gblob.reload()
        self._size_in_bytes = self.gblob.size

    def update_filename(self, filename: str):
        """Set the ContentDisposition metadata so that when a file is downloaded
        it has a human-readable name.
        """

        if '"' in filename:
            raise ValueError(f'Filename is not allowed to have double quote in it: {filename!r}')

        self.gblob.content_disposition = f'attachment; filename="{filename}"'
        self.gblob.patch()

    def get_url(self, *, is_public: bool) -> str:
        if is_public:
            return self.gblob.public_url

        expiration = datetime.datetime.utcnow() + datetime.timedelta(days=1)
        return self.gblob.generate_signed_url(expiration)

    def make_public(self):
        self.gblob.make_public()

    def exists(self) -> bool:
        # Reload to get the actual file properties from Google.
        try:
            self.gblob.reload()
        except gcloud_exc.NotFound:
            return False
        return self.gblob.exists()


def update_file_name(node):
    """Assign to the CGS blob the same name of the asset node. This way when
    downloading an asset we get a human-readable name.
    """

    # Process only files that are not processing
    if node['properties'].get('status', '') == 'processing':
        return

    def _format_name(name, override_ext, size=None, map_type=''):
        root, _ = os.path.splitext(name)
        size = '-{}'.format(size) if size else ''
        map_type = '-{}'.format(map_type) if map_type else ''
        return '{}{}{}{}'.format(root, size, map_type, override_ext)

    def _update_name(file_id, file_props):
        files_collection = current_app.data.driver.db['files']
        file_doc = files_collection.find_one({'_id': ObjectId(file_id)})

        if file_doc is None or file_doc.get('backend') != 'gcs':
            return

        # For textures -- the map type should be part of the name.
        map_type = file_props.get('map_type', '')

        storage = GoogleCloudStorageBucket(str(node['project']))
        blob = storage.get_blob(file_doc['file_path'])
        if blob is None:
            log.warning('Unable to find blob for file %s in project %s',
                        file_doc['file_path'], file_doc['project'])
            return

        # Pick file extension from original filename
        _, ext = os.path.splitext(file_doc['filename'])
        name = _format_name(node['name'], ext, map_type=map_type)
        blob.update_filename(name)

        # Assign the same name to variations
        for v in file_doc.get('variations', []):
            _, override_ext = os.path.splitext(v['file_path'])
            name = _format_name(node['name'], override_ext, v['size'], map_type=map_type)
            blob = storage.get_blob(v['file_path'])
            if blob is None:
                log.info('Unable to find blob for file %s in project %s. This can happen if the '
                         'video encoding is still processing.', v['file_path'], node['project'])
                continue
            blob.update_filename(name)

    # Currently we search for 'file' and 'files' keys in the object properties.
    # This could become a bit more flexible and realy on a true reference of the
    # file object type from the schema.
    if 'file' in node['properties']:
        _update_name(node['properties']['file'], {})

    if 'files' in node['properties']:
        for file_props in node['properties']['files']:
            _update_name(file_props['file'], file_props)
