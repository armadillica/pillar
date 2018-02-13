import pathlib
from unittest import mock

from pillar.tests import AbstractPillarTest

from bson import ObjectId


class ProjectMergerTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        super().setUp(**kwargs)

        self.pid_from, self.uid_from = self.create_project_with_admin(
            24 * 'a', project_overrides={'url': 'from-url'})
        self.pid_to, self.uid_to = self.create_project_with_admin(
            24 * 'b', project_overrides={'url': 'to-url'})
        self.create_valid_auth_token(24 * 'a', 'from-token')
        self.create_valid_auth_token(24 * 'b', 'to-token')

    def test_move_happy(self):
        import pillar.tests.common_test_data as ctd
        from pillar.api.file_storage_backends.local import LocalBucket

        fid = self._create_file_with_files()
        nid = self.create_node({
            **ctd.EXAMPLE_NODE,
            'picture': fid,
            'properties': {'file': fid},
            'project': self.pid_from,
        })

        from pillar.api.projects import merging

        with self.app.app_context():
            merging.merge_project(self.pid_from, self.pid_to)

        db_file = self.get(f'/api/files/{fid}').json()
        db_node = self.get(f'/api/nodes/{nid}').json()

        self.assertEqual(db_file['project'], str(self.pid_to))
        self.assertEqual(db_node['project'], str(self.pid_to))

        # Check the old and new locations of the files
        with self.app.app_context():
            self._assert_files_exist(LocalBucket(self.pid_to), db_file)
            self._assert_files_exist(LocalBucket(self.pid_from), db_file)

    def _assert_files_exist(self, bucket, db_file):
        for var in [db_file] + db_file['variations']:
            fname = var['file_path']
            blob = bucket.blob(fname)
            self.assertTrue(blob.exists(),
                            f'blob for file {fname} does not exist in bucket {bucket}')

    def _create_file_with_files(self):
        import io
        from pillar.api.file_storage_backends.local import LocalBucket

        fid, db_file = self.ensure_file_exists({
            '_id': ObjectId(f'ffff{20 * "a"}'),
            'project': self.pid_from,
            'backend': 'local',
        })

        # Make sure the files on the filesystem exist.
        with self.app.app_context():
            bucket = LocalBucket(db_file['project'])
            for var in [db_file] + db_file['variations']:
                fname = var['file_path']

                contents = io.BytesIO(fname.encode())
                blob = bucket.blob(fname)
                blob.create_from_file(contents, content_type='text/plain')

        return fid
