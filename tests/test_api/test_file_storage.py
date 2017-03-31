import io
import json
import os
import tempfile

import pillar.tests.common_test_data as ctd
import rsa.randnum
from pillar.tests import AbstractPillarTest, TEST_EMAIL_ADDRESS
from werkzeug.datastructures import FileStorage


class FileStorageTest(AbstractPillarTest):
    def fake_file(self, filename, content_type):
        return FileStorage(filename=filename,
                           name='file',  # form field name
                           content_type=content_type)

    def test_override_content_type(self):
        from pillar.api.file_storage import override_content_type

        fake = self.fake_file('compressed.blend', 'jemoeder')
        override_content_type(fake)
        self.assertEqual('application/x-blender', fake.content_type)
        self.assertEqual('application/x-blender', fake.mimetype)

        fake = self.fake_file('blend.mp3', 'application/octet-stream')
        override_content_type(fake)
        self.assertEqual('audio/mpeg', fake.content_type)
        self.assertEqual('audio/mpeg', fake.mimetype)

        # Official one is audio/mpeg, but if the browser gives audio/XXX, it should
        # just be used.
        fake = self.fake_file('blend.mp3', 'audio/mp3')
        override_content_type(fake)
        self.assertEqual('audio/mp3', fake.content_type)
        self.assertEqual('audio/mp3', fake.mimetype)

        fake = self.fake_file('mp3.mkv', 'application/octet-stream')
        override_content_type(fake)
        self.assertEqual('video/x-matroska', fake.content_type)
        self.assertEqual('video/x-matroska', fake.mimetype)

        fake = self.fake_file('mkv.mp3.avi.mp4', 'application/octet-stream')
        override_content_type(fake)
        self.assertEqual('video/mp4', fake.content_type)
        self.assertEqual('video/mp4', fake.mimetype)

        fake = self.fake_file('mkv.mp3.avi.mp4.unknown', 'application/awesome-type')
        override_content_type(fake)
        self.assertEqual('application/awesome-type', fake.content_type)
        self.assertEqual('application/awesome-type', fake.mimetype)


class TempDirTest(AbstractPillarTest):
    def test_tempfiles_location(self):
        # After importing the application, tempfiles should be created in the STORAGE_DIR
        storage = self.app.config['STORAGE_DIR']
        self.assertEqual(os.environ['TMP'], storage)
        self.assertNotIn('TEMP', os.environ)
        self.assertNotIn('TMPDIR', os.environ)

        handle, filename = tempfile.mkstemp()
        os.close(handle)
        dirname = os.path.dirname(filename)
        self.assertEqual(dirname, storage)

        tmpfile = tempfile.NamedTemporaryFile()
        dirname = os.path.dirname(tmpfile.name)
        self.assertEqual(dirname, storage)


class FileAccessTest(AbstractPillarTest):
    def __test_link_stripping(self):
        """Subscribers should get all links, but non-subscribers only a subset."""

        img_file_id, _ = self.ensure_file_exists()
        video_file_id, _ = self.ensure_file_exists({
            '_id': None,
            'content_type': 'video/matroska',
            'variations': [
                {
                    'format': 'mp4',
                    'height': 446,
                    'width': 1064,
                    'length': 219399183,
                    'link': 'https://hosting/filename.mp4',
                    'content_type': 'video/mp4',
                    'duration': 44,
                    'size': '446p',
                    'file_path': 'c1/c1f7b71c248c03468b2bb3e7c9f0c4e5cdb9d6d0.mp4',
                    'md5': 'c1f7b71c248c03468b2bb3e7c9f0c4e5cdb9d6d0'
                },
                {
                    'format': 'webm',
                    'height': 446,
                    'width': 1064,
                    'length': 31219520,
                    'link': 'https://hosting/filename.webm',
                    'content_type': 'video/webm',
                    'duration': 44,
                    'md5': 'c1f7b71c248c03468b2bb3e7c9f0c4e5cdb9d6d0',
                    'file_path': 'c1/c1f7b71c248c03468b2bb3e7c9f0c4e5cdb9d6d0.webm',
                    'size': '446p'
                }
            ]

        })
        blend_file_id, _ = self.ensure_file_exists({'_id': None,
                                                    'content_type': 'application/x-blender',
                                                    'variations': None})

        nonsub_user_id = self.create_user(user_id='cafef00dcafef00d00000000', roles=())
        sub_user_id = self.create_user(user_id='cafef00dcafef00dcafef00d', roles=('subscriber',))
        demo_user_id = self.create_user(user_id='cafef00dcafef00ddeadbeef', roles=('demo',))
        admin_user_id = self.create_user(user_id='aaaaaaaaaaaaaaaaaaaaaaaa', roles=('admin',))

        self.create_valid_auth_token(nonsub_user_id, 'nonsub-token')
        self.create_valid_auth_token(sub_user_id, 'sub-token')
        self.create_valid_auth_token(demo_user_id, 'demo-token')
        self.create_valid_auth_token(admin_user_id, 'admin-token')

        def assert_variations(file_id, has_access, token=None):
            if token:
                headers = {'Authorization': self.make_header(token)}
            else:
                headers = None
            resp = self.client.get('/api/files/%s' % file_id, headers=headers)
            self.assertEqual(200, resp.status_code)
            file_info = json.loads(resp.data)

            self.assertEqual(has_access, 'link' in file_info)
            self.assertEqual(has_access, 'link_expires' in file_info)
            return file_info

        # Unauthenticated user and non-subscriber should still get the file, but limited.
        file_info = assert_variations(img_file_id, False)
        self.assertEqual({'t', 'h', 'b'}, {var['size'] for var in file_info['variations']})
        file_info = assert_variations(img_file_id, False, 'nonsub-token')
        self.assertEqual({'t', 'h', 'b'}, {var['size'] for var in file_info['variations']})

        # Authenticated subscribers, demos and admins should get the full file.
        file_info = assert_variations(img_file_id, True, 'sub-token')
        self.assertEqual({'t', 'h', 'b'}, {var['size'] for var in file_info['variations']})
        file_info = assert_variations(img_file_id, True, 'demo-token')
        self.assertEqual({'t', 'h', 'b'}, {var['size'] for var in file_info['variations']})
        file_info = assert_variations(img_file_id, True, 'admin-token')
        self.assertEqual({'t', 'h', 'b'}, {var['size'] for var in file_info['variations']})

        # Unauthenticated user and non-subscriber should get no links what so ever.
        file_info = assert_variations(video_file_id, False)
        self.assertEqual([], file_info['variations'])
        file_info = assert_variations(video_file_id, False, 'nonsub-token')
        self.assertEqual([], file_info['variations'])

        # Authenticated subscribers, demos and admins should get the full file.
        file_info = assert_variations(video_file_id, True, 'sub-token')
        self.assertEqual({'mp4', 'webm'}, {var['format'] for var in file_info['variations']})
        file_info = assert_variations(video_file_id, True, 'demo-token')
        self.assertEqual({'mp4', 'webm'}, {var['format'] for var in file_info['variations']})
        file_info = assert_variations(video_file_id, True, 'admin-token')
        self.assertEqual({'mp4', 'webm'}, {var['format'] for var in file_info['variations']})

        # Unauthenticated user and non-subscriber should get no links what so ever.
        file_info = assert_variations(blend_file_id, False)
        self.assertIsNone(file_info['variations'])
        file_info = assert_variations(blend_file_id, False, 'nonsub-token')
        self.assertIsNone(file_info['variations'])

        # Authenticated subscribers, demos and admins should get the full file.
        file_info = assert_variations(blend_file_id, True, 'sub-token')
        self.assertIsNone(file_info['variations'])
        file_info = assert_variations(blend_file_id, True, 'demo-token')
        self.assertIsNone(file_info['variations'])
        file_info = assert_variations(blend_file_id, True, 'admin-token')
        self.assertIsNone(file_info['variations'])


class FileMaxSizeTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        AbstractPillarTest.setUp(self, **kwargs)

        self.project_id, _ = self.ensure_project_exists()
        self.user_id = self.create_user(groups=[ctd.EXAMPLE_ADMIN_GROUP_ID],
                                        roles=set())
        self.create_valid_auth_token(self.user_id, 'token')

    def test_upload_small_file(self):
        file_size = 10 * 2 ** 10
        test_file = self.create_test_file(file_size)

        resp = self.post('/api/storage/stream/%s' % self.project_id,
                         expected_status=201,
                         auth_token='token',
                         files={'file': (test_file, 'test_file.bin')})
        stream_info = resp.json()
        file_id = stream_info['file_id']

        self.assert_file_doc_ok(file_id, file_size)

    def test_upload_too_large_file(self):
        file_size = 30 * 2 ** 10
        test_file = self.create_test_file(file_size)

        self.post('/api/storage/stream/%s' % self.project_id,
                  expected_status=413,
                  auth_token='token',
                  files={'file': (test_file, 'test_file.bin')})

    def test_upload_large_file_subscriber(self):
        self.badger(TEST_EMAIL_ADDRESS, 'subscriber', 'grant')

        file_size = 30 * 2 ** 10
        test_file = self.create_test_file(file_size)

        resp = self.post('/api/storage/stream/%s' % self.project_id,
                         expected_status=201,
                         auth_token='token',
                         files={'file': (test_file, 'test_file.bin')})
        stream_info = resp.json()
        file_id = stream_info['file_id']

        self.assert_file_doc_ok(file_id, file_size)

    def assert_file_doc_ok(self, file_id, file_size):
        with self.app.test_request_context():
            from pillar.api.utils import str2id

            # Check that the file exists in MongoDB
            files_coll = self.app.data.driver.db['files']
            db_file = files_coll.find_one({'_id': str2id(file_id)})
            self.assertEqual(file_size, db_file['length'])

    def create_test_file(self, file_size_bytes):
        fileob = io.BytesIO(rsa.randnum.read_random_bits(file_size_bytes * 8))
        return fileob


class VideoSizeTest(AbstractPillarTest):
    def test_video_size(self):
        from pillar.api import file_storage
        from pathlib import Path

        fname = Path(__file__).with_name('video-tiny.mkv')

        with self.app.test_request_context():
            size = file_storage._video_size_pixels(fname)

        self.assertEqual((960, 540), size)

    def test_video_size_nonexistant(self):
        from pillar.api import file_storage
        from pathlib import Path

        fname = Path(__file__).with_name('video-nonexistant.mkv')

        with self.app.test_request_context():
            size = file_storage._video_size_pixels(fname)

        self.assertEqual((0, 0), size)

    def test_video_cap_at_1080(self):
        from pillar.api import file_storage

        # Up to 1920x1080, the input should be returned as-is.
        self.assertEqual((0, 0), file_storage._video_cap_at_1080(0, 0))
        self.assertEqual((1, 1), file_storage._video_cap_at_1080(1, 1))
        self.assertEqual((960, 540), file_storage._video_cap_at_1080(960, 540))
        self.assertEqual((1920, 540), file_storage._video_cap_at_1080(1920, 540))

        # The height must be multiple of 8
        self.assertEqual((1920, 784), file_storage._video_cap_at_1080(2048, 840))

        # The width must be multiple of 16
        self.assertEqual((1024, 1080), file_storage._video_cap_at_1080(1920, 2000))

        # Resizing the height based on the width will still produce a too high video,
        # so this one hits both resize branches in one call:
        self.assertEqual((1104, 1080), file_storage._video_cap_at_1080(2048, 2000))

        size = file_storage._video_cap_at_1080(2048, 2000)
        self.assertIsInstance(size[0], int)
        self.assertIsInstance(size[1], int)
