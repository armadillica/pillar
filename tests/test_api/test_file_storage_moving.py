import datetime

import responses

from pillar.tests import AbstractPillarTest

# Always do a final test run (and commit with) assert_all_requests_are_fired=True.
# Setting it to False can help track down other issues, though, that can be masked
# by the error of RequestsMock.
mock = responses.RequestsMock(
    assert_all_requests_are_fired=True
    # assert_all_requests_are_fired=False
)


class ChangeBackendTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        AbstractPillarTest.setUp(self, **kwargs)

        self.project_id, self.project = self.ensure_project_exists()
        responses.assert_all_requests_are_fired = True

    @mock.activate
    def test_file_and_variations(self):
        from pillar.api.file_storage import moving, generate_link

        image_file_id, fdoc = self._create_image_file_doc()

        # Expect GETs on regenerated links.
        mock.add(mock.GET,
                 generate_link('unittest', fdoc['file_path']),
                 body='file-content',
                 content_type='image/jpeg')

        for variation in fdoc['variations']:
            mock.add(mock.GET,
                     generate_link('unittest', variation['file_path']),
                     body='file-content',
                     content_type='image/jpeg')

        with self.app.test_request_context():
            moving.change_file_storage_backend(image_file_id, 'gcs')

            # Check that the file document has been updated correctly
            files_coll = self.app.data.driver.db['files']
            fdoc = files_coll.find_one(image_file_id)

        self.assertEqual('gcs', fdoc['backend'])
        self.assertIn('/path/to/testing/gcs/', fdoc['link'])

        for variation in fdoc['variations']:
            self.assertIn('/path/to/testing/gcs/', variation['link'])

    @mock.activate
    def test_only_variations(self):
        from pillar.api.file_storage import moving, generate_link

        image_file_id, fdoc = self._create_image_file_doc()

        # Expect GETs on regenerated links.
        mock.add(mock.GET,
                 generate_link('unittest', fdoc['file_path']),
                 status=404)

        for variation in fdoc['variations']:
            mock.add(mock.GET,
                     generate_link('unittest', variation['file_path']),
                     body='file-content',
                     content_type='image/jpeg')

        with self.app.test_request_context():
            moving.change_file_storage_backend(image_file_id, 'gcs')

            # Check that the file document has been updated correctly
            files_coll = self.app.data.driver.db['files']
            fdoc = files_coll.find_one(image_file_id)

        self.assertEqual('gcs', fdoc['backend'])
        self.assertIn('/path/to/testing/gcs/', fdoc['link'])

        for variation in fdoc['variations']:
            self.assertIn('/path/to/testing/gcs/', variation['link'])

    @mock.activate
    def test_no_variations(self):
        from pillar.api.file_storage import moving, generate_link

        image_file_id, fdoc = self._create_image_file_doc(variations=False)

        # Expect GETs on regenerated links.
        mock.add(mock.GET,
                 generate_link('unittest', fdoc['file_path']),
                 body='file-content',
                 content_type='image/jpeg')

        with self.app.test_request_context():
            moving.change_file_storage_backend(image_file_id, 'gcs')

            # Check that the file document has been updated correctly
            files_coll = self.app.data.driver.db['files']
            fdoc = files_coll.find_one(image_file_id)

        self.assertEqual('gcs', fdoc['backend'])
        self.assertIn('/path/to/testing/gcs/', fdoc['link'])

    def _create_image_file_doc(self, variations=True):
        fdoc = {'status': 'complete', 'name': 'some-hash.jpg', 'backend': 'unittest',
                'format': 'jpeg',
                'filename': 'image-micak.jpg', 'project': self.project_id, 'length': 2708160,
                'content_type': 'image/jpeg', 'file_path': '3c61e953ee644786b98027e043fd3af3.jpg',
                'length_aggregate_in_bytes': 3196056,
                'link': 'https://server.cdnsun/projid/_%2Fsome-hash.jpg',
                'link_expires': datetime.datetime(2016, 8, 23, 15, 23, 48), 'md5': '',}

        if variations:
            fdoc['variations'] = [
                {'length': 3312, 'link': 'https://server.cdnsun/projid/_%2Fsome-hash-b.jpg',
                 'content_type': 'image/jpeg',
                 'file_path': '3c61e953ee644786b98027e043fd3af3-b.jpg', 'size': 'b', 'md5': ''},
                {'height': 2048, 'width': 2048, 'length': 381736,
                 'link': 'https://server.cdnsun/projid/_%2Fsome-hash-h.jpg',
                 'content_type': 'image/jpeg', 'md5': '',
                 'file_path': '3c61e953ee644786b98027e043fd3af3-h.jpg', 'size': 'h'},
                {'height': 320, 'width': 320, 'length': 8818,
                 'link': 'https://server.cdnsun/projid/_%2Fsome-hash-m.jpg',
                 'content_type': 'image/jpeg', 'md5': '',
                 'file_path': '3c61e953ee644786b98027e043fd3af3-m.jpg', 'size': 'm'},
                {'height': 1024, 'width': 1024, 'length': 89012,
                 'link': 'https://server.cdnsun/projid/_%2Fsome-hash-l.jpg',
                 'content_type': 'image/jpeg', 'md5': '',
                 'file_path': '3c61e953ee644786b98027e043fd3af3-l.jpg', 'size': 'l'},
                {'height': 90, 'width': 90, 'length': 1774,
                 'link': 'https://server.cdnsun/projid/_%2Fsome-hash-s.jpg',
                 'content_type': 'image/jpeg', 'md5': '',
                 'file_path': '3c61e953ee644786b98027e043fd3af3-s.jpg', 'size': 's'},
                {'height': 160, 'width': 160, 'length': 3244,
                 'link': 'https://server.cdnsun/projid/_%2Fsome-hash-t.jpg',
                 'content_type': 'image/jpeg', 'is_public': True, 'md5': '',
                 'file_path': '3c61e953ee644786b98027e043fd3af3-t.jpg', 'size': 't'}]

        with self.app.test_request_context():
            files_coll = self.app.data.driver.db['files']

            result = files_coll.insert_one(fdoc)
            file_id = result.inserted_id

            # Re-fetch from the database, so that we're sure we return the same as is stored.
            # This is necessary as datetimes are rounded by MongoDB.
            from_db = files_coll.find_one(file_id)
            return file_id, from_db
