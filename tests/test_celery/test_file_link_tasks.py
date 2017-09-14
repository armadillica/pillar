import datetime

from bson import ObjectId, tz_util
from dateutil.parser import parse

from pillar.tests import AbstractPillarTest
from pillar.tests import common_test_data as ctd

EXAMPLE_FILE = {
    '_created': datetime.datetime(2015, 12, 17, 16, 28, 49, tzinfo=tz_util.utc),
    '_updated': datetime.datetime(2016, 3, 25, 10, 28, 24, tzinfo=tz_util.utc),
    '_etag': '044ce3aede2e123e261c0d8bd77212f264d4f7b0',
    'height': 2048,
    'name': 'c2a5c897769ce1ef0eb10f8fa1c472bcb8e2d5a4.png', 'format': 'png',
    'variations': [
        {'format': 'jpg', 'height': 160, 'width': 160, 'length': 8558,
         'link': 'http://localhost:8002/file-variant-h', 'content_type': 'image/jpeg',
         'md5': '--', 'file_path': 'c2a5c897769ce1ef0eb10f8fa1c472bcb8e2d5a4-b.jpg',
         'size': 'b'},
        {'format': 'jpg', 'height': 2048, 'width': 2048, 'length': 819569,
         'link': 'http://localhost:8002/file-variant-h', 'content_type': 'image/jpeg',
         'md5': '--', 'file_path': 'c2a5c897769ce1ef0eb10f8fa1c472bcb8e2d5a4-h.jpg',
         'size': 'h'},
        {'format': 'jpg', 'height': 64, 'width': 64, 'length': 8195,
         'link': 'http://localhost:8002/file-variant-t', 'content_type': 'image/jpeg',
         'md5': '--', 'file_path': 'c2a5c897769ce1ef0eb10f8fa1c472bcb8e2d5a4-t.jpg',
         'size': 't'},
    ],
    'filename': 'brick_dutch_soft_bump.png',
    'project': ctd.EXAMPLE_PROJECT_ID,
    'width': 2048,
    'length': 6227670,
    'user': ObjectId('56264fc4fa3a250344bd10c5'),
    'content_type': 'image/png',
    'file_path': 'c2a5c897769ce1ef0eb10f8fa1c472bcb8e2d5a4.png',
    'backend': 'pillar',
    'link': 'http://localhost:8002/file',
}


class FileLinkCeleryTasksTest(AbstractPillarTest):
    def ensure_file_exists(self, file_overrides=None, **kwargs) -> (ObjectId, dict):
        """Same as in superclass, but different EXAMPLE_FILE."""
        return super().ensure_file_exists(file_overrides, example_file=EXAMPLE_FILE)

    def test_refresh_all_files(self):
        self.enter_app_context()

        now = datetime.datetime.now(tz=tz_util.utc)

        # No expiry known → refresh
        fid1, _ = self.ensure_file_exists({'backend': 'gcs'})
        # Expired → refresh
        fid2, _ = self.ensure_file_exists({'backend': 'gcs', 'link_expires': parse('2016-01-01')})
        # Going to expire within 2 hours → refresh
        fid3, _ = self.ensure_file_exists({
            'backend': 'gcs',
            'link_expires': now + datetime.timedelta(hours=1, minutes=57)})
        # Not same backend → ignore
        fid4, file_4 = self.ensure_file_exists({
            'backend': 'pillar',
            'link_expires': now + datetime.timedelta(hours=1, minutes=58)})
        # Same as fid3 → refresh
        fid5, _ = self.ensure_file_exists({
            'backend': 'gcs',
            'link_expires': now + datetime.timedelta(hours=1, minutes=58)})
        # Valid for long enough → ignore
        fid6, file_6 = self.ensure_file_exists({
            'backend': 'gcs',
            'link_expires': now + datetime.timedelta(hours=5)})
        # Expired but deleted → ignore
        fid7, file_7 = self.ensure_file_exists({
            '_deleted': True,
            'backend': 'gcs',
            'link_expires': now + datetime.timedelta(hours=-5)})
        # Expired but would be the 5th in a 4-file chunk → ignore
        fid8, file_8 = self.ensure_file_exists({
            'backend': 'gcs',
            'link_expires': now + datetime.timedelta(hours=1, minutes=59)})

        from pillar.celery import file_link_tasks as flt

        flt.regenerate_all_expired_links('gcs', 4)

        files_coll = self.app.db('files')

        # Test files that are supposed to be refreshed.
        expected_refresh = {'fid1': fid1, 'fid2': fid2, 'fid3': fid3, 'fid5': fid5}
        for name, fid in expected_refresh.items():
            from_db = files_coll.find_one(fid)

            self.assertIn('link_expires', from_db, f'checking {name}')
            self.assertGreater(from_db['link_expires'], now, f'checking {name}')

        # Test files that shouldn't have been touched.
        expected_untouched = {'fid4': (fid4, file_4),
                              'fid6': (fid6, file_6),
                              'fid7': (fid7, file_7),
                              'fid8': (fid8, file_8)}
        for name, (fid, before) in expected_untouched.items():
            from_db = files_coll.find_one(fid)
            self.assertEqual(from_db['link_expires'], before['link_expires'], f'checking {name}')
