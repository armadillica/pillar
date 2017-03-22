import typing

from pillar.tests import AbstractPillarTest


class LocalStorageBackendTest(AbstractPillarTest):
    def create_test_file(self) -> (typing.IO, bytes):
        import io
        import secrets

        file_contents = secrets.token_bytes(512)
        test_file: typing.IO = io.BytesIO(file_contents)

        return test_file, file_contents

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

        resp = self.get(url)

        self.assertEqual(200, resp.status_code)
        self.assertEqual('512', resp.headers['Content-Length'])
        self.assertEqual(file_contents, resp.data)

    def storage_backend(self):
        from pillar.api.file_storage_backends import Bucket

        return Bucket.for_backend('local')

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
