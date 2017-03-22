import typing
from unittest import mock

from pillar.tests import AbstractPillarTest


class AbstractStorageBackendTest(AbstractPillarTest):
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


class MockedGoogleCloudStorageTest(AbstractStorageBackendTest):
    def storage_backend(self):
        from pillar.api.file_storage_backends import Bucket

        return Bucket.for_backend('gcs')

    def test_file_upload(self):
        import pillar.api.file_storage_backends.gcs as gcs
        from gcloud.storage import Client, Bucket, Blob

        # Set up mock GCS client
        mock_gcs_client = gcs.gcs = mock.MagicMock(name='mock_gcs_client', autospec=Client)
        mock_bucket = mock.MagicMock(name='mock_bucket', autospec=Bucket)
        mock_blob = mock.MagicMock(name='mock_blob', autospec=Blob)

        mock_gcs_client.get_bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        mock_blob.public_url = '/path/to/somefile.bin'
        mock_blob.size = 318

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

        mock_blob.upload_from_file.assert_called_with(test_file,
                                                      size=512,
                                                      content_type='application/octet-stream')
        mock_blob.reload.assert_called_once()
