import json

import os
import tempfile

from werkzeug.datastructures import FileStorage

from common_test_class import AbstractPillarTest


class FileStorageTest(AbstractPillarTest):
    def fake_file(self, filename, content_type):
        return FileStorage(filename=filename,
                           name='file',  # form field name
                           content_type=content_type)

    def test_override_content_type(self):
        from application.modules.file_storage import override_content_type

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
            u'_id': None,
            u'content_type': u'video/matroska',
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
        blend_file_id, _ = self.ensure_file_exists({u'_id': None,
                                                    u'content_type': u'application/x-blender',
                                                    u'variations': None})

        nonsub_user_id = self.create_user(user_id='cafef00dcafef00d00000000', roles=())
        sub_user_id = self.create_user(user_id='cafef00dcafef00dcafef00d', roles=(u'subscriber',))
        demo_user_id = self.create_user(user_id='cafef00dcafef00ddeadbeef', roles=(u'demo',))
        admin_user_id = self.create_user(user_id='aaaaaaaaaaaaaaaaaaaaaaaa', roles=(u'admin',))

        self.create_valid_auth_token(nonsub_user_id, 'nonsub-token')
        self.create_valid_auth_token(sub_user_id, 'sub-token')
        self.create_valid_auth_token(demo_user_id, 'demo-token')
        self.create_valid_auth_token(admin_user_id, 'admin-token')

        def assert_variations(file_id, has_access, token=None):
            if token:
                headers = {'Authorization': self.make_header(token)}
            else:
                headers = None
            resp = self.client.get('/files/%s' % file_id, headers=headers)
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
