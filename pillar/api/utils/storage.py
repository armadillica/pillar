"""Utility for managing storage backends and files."""

import abc
import logging
import os
import shutil
import typing

from bson import ObjectId
from flask import current_app

from pillar.api import utils
from pillar.api.utils.authorization import user_has_role
from pillar.api.utils.imaging import generate_local_thumbnails

log = logging.getLogger(__name__)


class Bucket(metaclass=abc.ABCMeta):
    """Can be a GCS bucket or simply a project folder in Pillar

    :type name: string
    :param name: Name of the bucket. As a convention, we use the ID of
    the project to name the bucket.

    """

    # Mapping from backend name to Bucket class
    backends = {}

    backend_name: str = None  # define in subclass.

    def __init__(self, name):
        self.name = name

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        assert cls.backend_name, '%s.backend_name must be non-empty string' % cls
        cls.backends[cls.backend_name] = cls

    @classmethod
    def for_backend(cls, backend_name: str) -> type:
        """Returns the Bucket subclass for the given backend."""
        return cls.backends[backend_name]

    @abc.abstractmethod
    def blob(self, blob_name) -> 'Blob':
        """Factory constructor for blob object.

        :type blob_name: string
        :param blob_name: The name of the blob to be instantiated.
        """
        return Blob(name=blob_name, bucket=self)

    @abc.abstractmethod
    def get_blob(self, blob_name) -> typing.Optional['Blob']:
        """Get a blob object by name.

        If the blob exists return the object, otherwise None.
        """
        pass


class Blob(metaclass=abc.ABCMeta):
    """A wrapper for file or blob objects.

    :type name: string
    :param name: Name of the blob.

    """

    def __init__(self, name: str, bucket: Bucket):
        self.name = name
        self.bucket = bucket
        self._size_in_bytes = None

    @property
    def size(self) -> typing.Optional[int]:
        """Size of the object, in bytes.

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

    @abc.abstractmethod
    def _process_image(self, file_doc):
        pass

    @abc.abstractmethod
    def _process_video(self, file_doc):
        pass

    # TODO Sybren: change file_id type to ObjectId?
    def process_file(self, file_id: str):
        """Generate image thumbnails or encode video.

        :type file_id: string
        :param file_id: The document ID for the file processed. We need it to
        update the document as we process the file.
        """

        def update_file_doc(file_id, **updates):
            res = files.update_one({'_id': ObjectId(file_id)},
                                   {'$set': updates})

            log.debug('update_file_doc(%s, %s): %i matched, %i updated.',
                      file_id, updates, res.matched_count, res.modified_count)
            return res

        file_id = ObjectId(file_id)

        # Fetch the src_file document from MongoDB.
        files = current_app.data.driver.db['files']
        src_file = files.find_one(file_id)
        if not src_file:
            log.warning(
                'process_file(%s): no such file document found, ignoring.')
            return

        # Update the 'format' field from the content type.
        # TODO: overrule the content type based on file extention & magic numbers.
        mime_category, src_file['format'] = src_file['content_type'].split('/', 1)

        # Prevent video handling for non-admins.
        if not user_has_role('admin') and mime_category == 'video':
            if src_file['format'].startswith('x-'):
                xified = src_file['format']
            else:
                xified = 'x-' + src_file['format']

            src_file['content_type'] = 'application/%s' % xified
            mime_category = 'application'
            log.info('Not processing video file %s for non-admin user', file_id)

        # Run the required processor, based on the MIME category.
        processors = {
            'image': self._process_image,
            'video': self._process_video,
        }

        try:
            processor = processors[mime_category]
        except KeyError:
            log.info("POSTed file %s was of type %r, which isn't "
                     "thumbnailed/encoded.", file_id,
                     mime_category)
            src_file['status'] = 'complete'
        else:
            log.debug('process_file(%s): marking file status as "processing"',
                      file_id)
            src_file['status'] = 'processing'
            update_file_doc(file_id, status='processing')

            try:
                processor(src_file)
            except Exception:
                log.warning('process_file(%s): error when processing file, '
                            'resetting status to '
                            '"queued_for_processing"', file_id, exc_info=True)
                update_file_doc(file_id, status='queued_for_processing')
                return

        src_file = utils.remove_private_keys(src_file)
        # Update the original file with additional info, e.g. image resolution
        r, _, _, status = current_app.put_internal('files', src_file,
                                                   _id=file_id)
        if status not in (200, 201):
            log.warning(
                'process_file(%s): status %i when saving processed file '
                'info to MongoDB: %s',
                file_id, status, r)


class LocalBucket(Bucket):
    backend_name = 'local'

    def blob(self, blob_name: str) -> 'LocalBlob':
        return LocalBlob(name=blob_name, bucket=self)

    def get_blob(self, blob_name: str) -> typing.Optional['LocalBlob']:
        # TODO: Check if file exists, otherwise None
        return self.blob(blob_name)


class LocalBlob(Blob):
    def __init__(self, name: str, bucket: LocalBucket):
        super().__init__(name=name, bucket=bucket)

        bucket_name = bucket.name
        self.partial_path = os.path.join(bucket_name[:2], bucket_name,
                                         name[:2], name)
        self.path = os.path.join(
            current_app.config['STORAGE_DIR'], self.partial_path)

    def create_from_file(self, uploaded_file: typing.io.BinaryIO, file_size: int):
        assert hasattr(uploaded_file, 'read')

        # Ensure path exists before saving
        directory = os.path.dirname(self.path)
        if not os.path.exists(directory):
            os.makedirs(directory)

        with open(self.path, 'wb') as outfile:
            shutil.copyfileobj(uploaded_file, outfile)

        self._size_in_bytes = file_size

    def _process_image(self, file_doc: dict):
        from PIL import Image

        im = Image.open(self.path)
        res = im.size
        file_doc['width'] = res[0]
        file_doc['height'] = res[1]

        # Generate previews
        log.info('Generating thumbnails for file %s', file_doc['_id'])
        file_doc['variations'] = generate_local_thumbnails(file_doc['name'],
                                                           self.path)

        # Send those previews to Google Cloud Storage.
        log.info('Uploading %i thumbnails for file %s to Google Cloud Storage '
                 '(GCS)', len(file_doc['variations']), file_doc['_id'])

        # TODO: parallelize this at some point.
        for variation in file_doc['variations']:
            fname = variation['file_path']
            if current_app.config['TESTING']:
                log.warning('  - NOT making thumbnails', fname)
            else:
                log.debug('  - Sending thumbnail %s to %s', fname, self.bucket)

                blob = self.bucket.blob(fname)
                with open(variation['local_path'], 'rb') as local_file:
                    blob.create_from_file(local_file, variation['length'])

            try:
                os.unlink(variation['local_path'])
            except OSError:
                log.warning(
                    'Unable to unlink %s, ignoring this but it will need '
                    'cleanup later.', variation['local_path'])

            del variation['local_path']

        log.info('Done processing file %s', file_doc['_id'])
        file_doc['status'] = 'complete'

    def _process_video(self, file_doc):
        pass


def default_storage_backend(name):
    from flask import current_app

    backend_name = current_app.config['STORAGE_BACKEND']
    backend_cls = Bucket.for_backend(backend_name)
    return backend_cls(name)
