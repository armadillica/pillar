"""Tests chunked refreshing of links."""
import json

from bson import ObjectId, tz_util
from pillar.tests import AbstractPillarTest
from datetime import datetime, timedelta


class LinkRefreshTest(AbstractPillarTest):
    # noinspection PyMethodOverriding
    def ensure_file_exists(self, file_overrides):
        file_id = file_overrides[u'_id']

        file_overrides.update({
            u'_id': ObjectId(file_id),
            u'name': '%s.png' % file_id,
            u'file_path': '%s.png' % file_id,
            u'backend': 'unittest',
        })

        return super(LinkRefreshTest, self).ensure_file_exists(file_overrides)

    def setUp(self, **kwargs):
        super(LinkRefreshTest, self).setUp(**kwargs)

        self.project_id, self.project = self.ensure_project_exists()
        self.now = datetime.now(tz=tz_util.utc)

        # All expired

        expiry = [datetime(2016, 3, 22, 9, 28, 1, tzinfo=tz_util.utc),
                  datetime(2016, 3, 22, 9, 28, 2, tzinfo=tz_util.utc),
                  datetime(2016, 3, 22, 9, 28, 3, tzinfo=tz_util.utc),
                  self.now + timedelta(minutes=30), self.now + timedelta(minutes=90), ]
        ids_and_files = [self.ensure_file_exists(file_overrides={
            u'_id': 'cafef00ddeadbeef0000000%i' % file_idx,
            u'link_expires': expiry})
                         for file_idx, expiry in enumerate(expiry)]

        self.file_id, self.file = zip(*ids_and_files)
        self.file = list(self.file)  # otherwise it's a tuple, which is immutable.

        # Get initial expiries from the database (it has a different precision than datetime).
        self.expiry = [file_doc['link_expires'] for file_doc in self.file]

        # Should be ordered by link expiry
        assert self.file[0]['link_expires'] < self.file[1]['link_expires']
        assert self.file[1]['link_expires'] < self.file[2]['link_expires']
        assert self.file[2]['link_expires'] < self.file[3]['link_expires']
        assert self.file[3]['link_expires'] < self.file[4]['link_expires']

        # Files 0-2 should be expired already
        assert self.file[2]['link_expires'] < self.now

        # Files 3-4 should not be expired yet
        assert self.now < self.file[3]['link_expires']

    def _reload_from_db(self):
        files_collection = self.app.data.driver.db['files']

        for idx, file_id in enumerate(self.file_id):
            self.file[idx] = files_collection.find_one(file_id)

    def test_link_refresh(self):
        hour_from_now = 3600
        validity_seconds = self.app.config['FILE_LINK_VALIDITY']['unittest']
        refreshed_lower_limit = self.now + timedelta(seconds=0.9 * validity_seconds)

        with self.app.test_request_context():
            from pillar.api import file_storage

            # First run: refresh files 0 and 1, don't touch 2-4 (due to chunking).
            file_storage.refresh_links_for_project(self.project_id, 2, hour_from_now)
            self._reload_from_db()
            self.assertLess(refreshed_lower_limit, self.file[0]['link_expires'])
            self.assertLess(refreshed_lower_limit, self.file[1]['link_expires'])
            self.assertEqual(self.expiry[2], self.file[2]['link_expires'])
            self.assertEqual(self.expiry[3], self.file[3]['link_expires'])
            self.assertEqual(self.expiry[4], self.file[4]['link_expires'])

            # Second run: refresh files 2 (expired) and 3 (within timedelta).
            file_storage.refresh_links_for_project(self.project_id, 2, hour_from_now)
            self._reload_from_db()
            self.assertLess(refreshed_lower_limit, self.file[0]['link_expires'])
            self.assertLess(refreshed_lower_limit, self.file[1]['link_expires'])
            self.assertLess(refreshed_lower_limit, self.file[2]['link_expires'])
            self.assertLess(refreshed_lower_limit, self.file[3]['link_expires'])
            self.assertEqual(self.expiry[4], self.file[4]['link_expires'])

            # Third run: refresh nothing, file 4 is out of timedelta.
            file_storage.refresh_links_for_project(self.project_id, 2, hour_from_now)
            self._reload_from_db()
            self.assertLess(refreshed_lower_limit, self.file[0]['link_expires'])
            self.assertLess(refreshed_lower_limit, self.file[1]['link_expires'])
            self.assertLess(refreshed_lower_limit, self.file[2]['link_expires'])
            self.assertLess(refreshed_lower_limit, self.file[3]['link_expires'])
            self.assertEqual(self.expiry[4], self.file[4]['link_expires'])

    def test_refresh_upon_fetch(self):
        """Test that expired links are refreshed when we fetch a file document."""

        validity_seconds = self.app.config['FILE_LINK_VALIDITY']['unittest']
        refreshed_lower_limit = self.now + timedelta(seconds=0.9 * validity_seconds)

        resp = self.client.get('/api/files/%s' % self.file_id[0])
        self.assertEqual(200, resp.status_code)

        # Test the returned document.
        file_doc = json.loads(resp.data)
        expires = datetime.strptime(file_doc['link_expires'],
                                    self.app.config['RFC1123_DATE_FORMAT'])
        expires = expires.replace(tzinfo=tz_util.utc)
        self.assertLess(refreshed_lower_limit, expires)

        # Test the database.
        with self.app.test_request_context():
            self._reload_from_db()
            self.assertLess(refreshed_lower_limit, self.file[0]['link_expires'])
