import typing

from pillar.tests import AbstractPillarTest


class LocalStorageBackendTest(AbstractPillarTest):

    def test_upload_download(self):
        import io
        import secrets

        from pillar.api.file_storage_backends import Bucket

        file_contents = secrets.token_bytes(512)
        test_file: typing.IO = io.BytesIO(file_contents)

        with self.app.test_request_context():
            bucket_class = Bucket.for_backend('local')
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
