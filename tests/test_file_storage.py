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
        self.assertEqual('application/x-blend', fake.content_type)
        self.assertEqual('application/x-blend', fake.mimetype)

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

