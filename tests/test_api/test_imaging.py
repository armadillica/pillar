import pathlib
import shutil
import tempfile

from pillar.tests import AbstractPillarTest


class ThumbnailTest(AbstractPillarTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.image_path = pathlib.Path(__file__).with_name('images')

    def setUp(self, **kwargs):
        super().setUp(**kwargs)
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = pathlib.Path(self._tmp.name)

    def tearDown(self):
        super().tearDown()
        self._tmp.cleanup()

    def _tmpcopy(self, image_fname: str) -> pathlib.Path:
        src = self.image_path / image_fname
        dst = self.tmp / image_fname
        shutil.copy(str(src), str(dst))
        return dst

    def _thumb_test(self, source):
        from PIL import Image
        from pillar.api.utils import imaging

        with self.app.app_context():
            # Almost same as in production, but less different sizes.
            self.app.config['UPLOADS_LOCAL_STORAGE_THUMBNAILS'] = {
                's': {'size': (90, 90), 'crop': True},
                'b': {'size': (160, 160), 'crop': True},
                't': {'size': (160, 160), 'crop': False},
                'm': {'size': (320, 320), 'crop': False},
            }

            thumbs = imaging.generate_local_thumbnails('มัสมั่น', source)

        # Remove the length field, it is can be hard to predict.
        for t in thumbs:
            t.pop('length')

        # Verify that the images can be loaded and have the advertised size.
        for t in thumbs:
            local_path = pathlib.Path(t['local_path'])
            im = Image.open(local_path)
            self.assertEqual((t['width'], t['height']), im.size)

        return thumbs

    def test_thumbgen_jpg(self):
        source = self._tmpcopy('512x512-8bit-rgb.jpg')
        thumbs = self._thumb_test(source)

        self.assertEqual(
            [
                {'size': 's',
                 'file_path': 'มัสมั่น-s.jpg',
                 'local_path': str(source.with_name('512x512-8bit-rgb-s.jpg')),
                 'width': 90, 'height': 90,
                 'md5': '',
                 'content_type': 'image/jpeg'},
                {'size': 'b',
                 'file_path': 'มัสมั่น-b.jpg',
                 'local_path': str(source.with_name('512x512-8bit-rgb-b.jpg')),
                 'width': 160, 'height': 160,
                 'md5': '',
                 'content_type': 'image/jpeg'},
                {'size': 't',
                 'file_path': 'มัสมั่น-t.jpg',
                 'local_path': str(source.with_name('512x512-8bit-rgb-t.jpg')),
                 'width': 160, 'height': 160,
                 'md5': '',
                 'content_type': 'image/jpeg',
                 'is_public': True},
                {'size': 'm',
                 'file_path': 'มัสมั่น-m.jpg',
                 'local_path': str(source.with_name('512x512-8bit-rgb-m.jpg')),
                 'width': 320, 'height': 320,
                 'md5': '',
                 'content_type': 'image/jpeg'},
            ],
            thumbs)

    def test_thumbgen_vertical(self):
        source = self._tmpcopy('300x512-8bit-rgb.jpg')
        thumbs = self._thumb_test(source)

        self.assertEqual(
            [
                {'size': 's',
                 'file_path': 'มัสมั่น-s.jpg',
                 'local_path': str(source.with_name('300x512-8bit-rgb-s.jpg')),
                 'width': 90, 'height': 90,
                 'md5': '',
                 'content_type': 'image/jpeg'},
                {'size': 'b',
                 'file_path': 'มัสมั่น-b.jpg',
                 'local_path': str(source.with_name('300x512-8bit-rgb-b.jpg')),
                 'width': 160, 'height': 160,
                 'md5': '',
                 'content_type': 'image/jpeg'},
                {'size': 't',
                 'file_path': 'มัสมั่น-t.jpg',
                 'local_path': str(source.with_name('300x512-8bit-rgb-t.jpg')),
                 'width': 93, 'height': 160,
                 'md5': '',
                 'content_type': 'image/jpeg',
                 'is_public': True},
                {'size': 'm',
                 'file_path': 'มัสมั่น-m.jpg',
                 'local_path': str(source.with_name('300x512-8bit-rgb-m.jpg')),
                 'width': 187, 'height': 320,
                 'md5': '',
                 'content_type': 'image/jpeg'},
            ],
            thumbs)

    def test_thumbgen_png_alpha(self):
        source = self._tmpcopy('512x512-8bit-rgba.png')
        thumbs = self._thumb_test(source)

        self.assertEqual(
            [
                {'size': 's',
                 'file_path': 'มัสมั่น-s.png',
                 'local_path': str(source.with_name('512x512-8bit-rgba-s.png')),
                 'width': 90, 'height': 90,
                 'md5': '',
                 'content_type': 'image/png'},
                {'size': 'b',
                 'file_path': 'มัสมั่น-b.png',
                 'local_path': str(source.with_name('512x512-8bit-rgba-b.png')),
                 'width': 160, 'height': 160,
                 'md5': '',
                 'content_type': 'image/png'},
                {'size': 't',
                 'file_path': 'มัสมั่น-t.png',
                 'local_path': str(source.with_name('512x512-8bit-rgba-t.png')),
                 'width': 160, 'height': 160,
                 'md5': '',
                 'content_type': 'image/png',
                 'is_public': True},
                {'size': 'm',
                 'file_path': 'มัสมั่น-m.png',
                 'local_path': str(source.with_name('512x512-8bit-rgba-m.png')),
                 'width': 320, 'height': 320,
                 'md5': '',
                 'content_type': 'image/png'},
            ],
            thumbs)

    def test_thumbgen_png_greyscale_alpha(self):
        source = self._tmpcopy('512x512-8bit-grey-alpha.png')
        thumbs = self._thumb_test(source)

        self.assertEqual(
            [
                {'size': 's',
                 'file_path': 'มัสมั่น-s.png',
                 'local_path': str(source.with_name('512x512-8bit-grey-alpha-s.png')),
                 'width': 90, 'height': 90,
                 'md5': '',
                 'content_type': 'image/png'},
                {'size': 'b',
                 'file_path': 'มัสมั่น-b.png',
                 'local_path': str(source.with_name('512x512-8bit-grey-alpha-b.png')),
                 'width': 160, 'height': 160,
                 'md5': '',
                 'content_type': 'image/png'},
                {'size': 't',
                 'file_path': 'มัสมั่น-t.png',
                 'local_path': str(source.with_name('512x512-8bit-grey-alpha-t.png')),
                 'width': 160, 'height': 160,
                 'md5': '',
                 'content_type': 'image/png',
                 'is_public': True},
                {'size': 'm',
                 'file_path': 'มัสมั่น-m.png',
                 'local_path': str(source.with_name('512x512-8bit-grey-alpha-m.png')),
                 'width': 320, 'height': 320,
                 'md5': '',
                 'content_type': 'image/png'},
            ],
            thumbs)

    def test_thumbgen_png_16bit(self):
        source = self._tmpcopy('512x256-16bit-rgb.png')
        thumbs = self._thumb_test(source)

        self.assertEqual(
            [
                {'size': 's',
                 'file_path': 'มัสมั่น-s.png',
                 'local_path': str(source.with_name('512x256-16bit-rgb-s.png')),
                 'width': 90, 'height': 90,
                 'md5': '',
                 'content_type': 'image/png'},
                {'size': 'b',
                 'file_path': 'มัสมั่น-b.png',
                 'local_path': str(source.with_name('512x256-16bit-rgb-b.png')),
                 'width': 160, 'height': 160,
                 'md5': '',
                 'content_type': 'image/png'},
                {'size': 't',
                 'file_path': 'มัสมั่น-t.png',
                 'local_path': str(source.with_name('512x256-16bit-rgb-t.png')),
                 'width': 160, 'height': 80,
                 'md5': '',
                 'content_type': 'image/png',
                 'is_public': True},
                {'size': 'm',
                 'file_path': 'มัสมั่น-m.png',
                 'local_path': str(source.with_name('512x256-16bit-rgb-m.png')),
                 'width': 320, 'height': 160,
                 'md5': '',
                 'content_type': 'image/png'},
            ],
            thumbs)

    def test_thumbgen_png_16bit_grey(self):
        source = self._tmpcopy('512x256-16bit-grey.png')
        thumbs = self._thumb_test(source)

        self.assertEqual(
            [
                {'size': 's',
                 'file_path': 'มัสมั่น-s.jpg',
                 'local_path': str(source.with_name('512x256-16bit-grey-s.jpg')),
                 'width': 90, 'height': 90,
                 'md5': '',
                 'content_type': 'image/jpeg'},
                {'size': 'b',
                 'file_path': 'มัสมั่น-b.jpg',
                 'local_path': str(source.with_name('512x256-16bit-grey-b.jpg')),
                 'width': 160, 'height': 160,
                 'md5': '',
                 'content_type': 'image/jpeg'},
                {'size': 't',
                 'file_path': 'มัสมั่น-t.jpg',
                 'local_path': str(source.with_name('512x256-16bit-grey-t.jpg')),
                 'width': 160, 'height': 80,
                 'md5': '',
                 'content_type': 'image/jpeg',
                 'is_public': True},
                {'size': 'm',
                 'file_path': 'มัสมั่น-m.jpg',
                 'local_path': str(source.with_name('512x256-16bit-grey-m.jpg')),
                 'width': 320, 'height': 160,
                 'md5': '',
                 'content_type': 'image/jpeg'},
            ],
            thumbs)

    def test_thumbgen_png_16bit_greyscale_alpha(self):
        source = self._tmpcopy('512x256-16bit-grey-alpha.png')
        thumbs = self._thumb_test(source)

        self.assertEqual(
            [
                {'size': 's',
                 'file_path': 'มัสมั่น-s.png',
                 'local_path': str(source.with_name('512x256-16bit-grey-alpha-s.png')),
                 'width': 90, 'height': 90,
                 'md5': '',
                 'content_type': 'image/png'},
                {'size': 'b',
                 'file_path': 'มัสมั่น-b.png',
                 'local_path': str(source.with_name('512x256-16bit-grey-alpha-b.png')),
                 'width': 160, 'height': 160,
                 'md5': '',
                 'content_type': 'image/png'},
                {'size': 't',
                 'file_path': 'มัสมั่น-t.png',
                 'local_path': str(source.with_name('512x256-16bit-grey-alpha-t.png')),
                 'width': 160, 'height': 80,
                 'md5': '',
                 'content_type': 'image/png',
                 'is_public': True},
                {'size': 'm',
                 'file_path': 'มัสมั่น-m.png',
                 'local_path': str(source.with_name('512x256-16bit-grey-alpha-m.png')),
                 'width': 320, 'height': 160,
                 'md5': '',
                 'content_type': 'image/png'},
            ],
            thumbs)
