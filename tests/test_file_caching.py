"""Test cases for the /files/{id} entrypoint, testing cache behaviour."""

import bson.tz_util
import datetime
from eve import RFC1123_DATE_FORMAT

from common_test_stuff import AbstractPillarTest


class FileCachingTest(AbstractPillarTest):

    def test_nonexistant_file(self):
        with self.app.test_request_context():
            resp = self.client.get('/files/12345')
        self.assertEqual(404, resp.status_code)

    def test_existing_file(self):
        file_id, _ = self._ensure_file_exists()

        resp = self.client.get('/files/%s' % file_id)
        self.assertEqual(200, resp.status_code)

    def test_if_modified_304(self):
        with self.app.test_request_context():
            # Make sure the file link has not expired.
            expires = datetime.datetime.now(tz=bson.tz_util.utc) + datetime.timedelta(minutes=1)
            file_id, file_doc = self._ensure_file_exists(file_overrides={
                u'link_expires': expires
            })

            updated = file_doc['_updated'].strftime(RFC1123_DATE_FORMAT)
            resp = self.client.get('/files/%s' % file_id,
                                   headers={'if_modified_since': updated})
        self.assertEqual(304, resp.status_code)

    def test_if_modified_200(self):
        file_id, file_doc = self._ensure_file_exists()

        delta = datetime.timedelta(days=-1)

        with self.app.test_request_context():
            updated = (file_doc['_updated'] + delta).strftime(RFC1123_DATE_FORMAT)
            resp = self.client.get('/files/%s' % file_id,
                                   headers={'if_modified_since': updated})
        self.assertEqual(200, resp.status_code)

    def test_if_modified_link_expired(self):
        with self.app.test_request_context():
            # Make sure the file link has expired.
            expires = datetime.datetime.now(tz=bson.tz_util.utc) - datetime.timedelta(seconds=1)
            file_id, file_doc = self._ensure_file_exists(file_overrides={
                u'link_expires': expires
            })

            updated = file_doc['_updated'].strftime(RFC1123_DATE_FORMAT)
            resp = self.client.get('/files/%s' % file_id,
                                   headers={'if_modified_since': updated})
        self.assertEqual(200, resp.status_code)
