import abc
import typing
from unittest import mock

from pillar.tests import AbstractPillarTest


class AbstractStorageBackendTest(AbstractPillarTest):
    @abc.abstractmethod
    def storage_backend(self):
        pass

    def create_test_file(self) -> (typing.IO, bytes):
        import io
        import secrets

        file_contents = secrets.token_bytes(512)
        test_file: typing.IO = io.BytesIO(file_contents)

        return test_file, file_contents

    def assert_valid_file(self, expected_file_contents: bytes, url: str):
        resp = self.get(url)

        self.assertEqual(200, resp.status_code)
        self.assertEqual(len(expected_file_contents), int(resp.headers['Content-Length']))
        self.assertEqual(expected_file_contents, resp.data)

    def do_test_rename(self):
        from pillar.api.file_storage_backends import Bucket

        test_file, file_contents = self.create_test_file()

        bucket_class: typing.Type[Bucket] = self.storage_backend()
        bucket = bucket_class(24 * 'a')

        blob = bucket.blob('somefile.bin')
        blob.create_from_file(test_file, content_type='application/octet-stream')

        new_blob = bucket.rename_blob(blob, 'ænother-näme.bin')
        return blob, new_blob


class LocalStorageBackendTest(AbstractStorageBackendTest):
    def storage_backend(self):
        from pillar.api.file_storage_backends import Bucket

        return Bucket.for_backend('local')

    def test_upload_download(self):
        test_file, file_contents = self.create_test_file()

        with self.app.test_request_context():
            bucket_class = self.storage_backend()
            bucket = bucket_class('buckettest')
            blob = bucket.blob('somefile.bin')

            # We should be able to upload the file, and then download it again
            # from the URL given by its blob.
            blob.create_from_file(test_file, file_size=512, content_type='application/octet-stream')
            url = blob.get_url(is_public=True)

        self.assert_valid_file(file_contents, url)

    def test_upload_from_path(self):
        import tempfile
        import pathlib

        test_file, file_contents = self.create_test_file()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file_path = pathlib.Path(tmpdir) / 'testfile.bin'

            with test_file_path.open('wb') as outfile:
                outfile.write(file_contents)

            with self.app.test_request_context():
                bucket_class = self.storage_backend()
                bucket = bucket_class('buckettest')
                blob = bucket.blob('somefile.bin')

                # We should be able to upload the file, and then download it again
                # from the URL given by its blob, even after the original file was removed.
                blob.upload_from_path(test_file_path, content_type='application/octet-stream')
                url = blob.get_url(is_public=True)

        self.assertFalse(test_file_path.exists())
        self.assert_valid_file(file_contents, url)

    def test_copy_to_bucket(self):
        from bson import ObjectId

        test_file, file_contents = self.create_test_file()

        src_project_id = ObjectId(24 * 'a')
        dest_project_id = ObjectId(24 * 'd')

        with self.app.test_request_context():
            bucket_class = self.storage_backend()
            bucket1 = bucket_class(str(src_project_id))
            src_blob = bucket1.blob('somefile.bin')
            src_blob.create_from_file(test_file, content_type='application/octet-stream')

            bucket_class.copy_to_bucket('somefile.bin', src_project_id, dest_project_id)

            # Test that the file now exists at the new bucket.
            bucket2 = bucket_class(str(dest_project_id))
            dest_blob = bucket2.blob('somefile.bin')
            url = dest_blob.get_url(is_public=True)

        resp = self.get(url)

        self.assertEqual(200, resp.status_code)
        self.assertEqual('512', resp.headers['Content-Length'])
        self.assertEqual(file_contents, resp.data)

    def test_exists(self):
        self.enter_app_context()
        test_file, file_contents = self.create_test_file()

        bucket_class = self.storage_backend()
        bucket = bucket_class(24 * 'a')

        blob = bucket.blob('somefile.bin')
        blob.create_from_file(test_file, content_type='application/octet-stream')

        self.assertTrue(blob.exists())
        self.assertFalse(bucket.blob('ütﬀ-8').exists())

    def test_rename(self):
        from pillar.api.file_storage_backends.local import LocalBlob

        self.enter_app_context()

        old_blob, new_blob = self.do_test_rename()
        assert isinstance(old_blob, LocalBlob)
        assert isinstance(new_blob, LocalBlob)

        self.assertTrue(new_blob.abspath().exists())
        self.assertFalse(old_blob.exists())

        self.assertEqual(old_blob.abspath().parent.parent,
                         new_blob.abspath().parent.parent)


class MockedGoogleCloudStorageTest(AbstractStorageBackendTest):
    def storage_backend(self):
        from pillar.api.file_storage_backends import Bucket

        return Bucket.for_backend('gcs')

    def mock_gcs(self):
        import pillar.api.file_storage_backends.gcs as gcs
        from gcloud.storage import Client, Bucket, Blob

        mock_gcs_client = gcs.gcs = mock.MagicMock(name='mock_gcs_client', autospec=Client)
        mock_bucket = mock.MagicMock(name='mock_bucket', autospec=Bucket)
        mock_blob = mock.MagicMock(name='mock_blob', autospec=Blob)
        mock_gcs_client.get_bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        mock_blob.public_url = '/path/to/somefile.bin'
        mock_blob.size = 318
        mock_blob.exists.return_value = True

        return mock_bucket, mock_blob

    def test_file_upload(self):
        _, mock_blob = self.mock_gcs()

        test_file, file_contents = self.create_test_file()

        with self.app.test_request_context():
            bucket_class = self.storage_backend()
            bucket = bucket_class('buckettest')
            blob = bucket.blob('somefile.bin')

            # We should be able to upload the file, and then download it again
            # from the URL given by its blob.
            blob.create_from_file(test_file, file_size=512, content_type='application/octet-stream')
            url = blob.get_url(is_public=True)
            self.assertIn('somefile.bin', url)

            # Google-reported size should take precedence over reality.
            self.assertEqual(318, blob.size)

            self.assertTrue(blob.exists())

        mock_blob.upload_from_file.assert_called_with(test_file,
                                                      size=512,
                                                      content_type='application/octet-stream')
        self.assertEqual(2, mock_blob.reload.call_count)

    def test_rename(self):
        self.enter_app_context()
        mock_bucket, mock_blob = self.mock_gcs()
        self.do_test_rename()

        # The storage API should have added the _ path in front.
        mock_bucket.rename_blob.assert_called_with(mock_blob, '_/ænother-näme.bin')
