"""Test cases for the zencoder notifications."""
import json

from pillar.tests import AbstractPillarTest


class SizeDescriptorTest(AbstractPillarTest):
    def test_known_sizes(self):
        from pillar.api.encoding import size_descriptor
        self.assertEqual('720p', size_descriptor(1280, 720))  # 720p at 16:9 aspect
        self.assertEqual('720p', size_descriptor(1280, 548))  # 720p at 21:9 aspect
        self.assertEqual('720p', size_descriptor(1280, 500))  # 720p at 23:9 aspect
        self.assertEqual('4k', size_descriptor(4096, 2304))  # 4k at 16:9 aspect
        self.assertEqual('4k', size_descriptor(4096, 1602))  # 4k at 23:9 aspect
        self.assertEqual('4k', size_descriptor(4096, 1602))  # 4k at 23:9 aspect
        self.assertEqual('UHD', size_descriptor(3840, 2160))  # UHD at 16:9 aspect

    def test_unknown_sizes(self):
        from pillar.api.encoding import size_descriptor
        self.assertEqual('240p', size_descriptor(320, 240))  # old VGA resolution


class ZencoderNotificationTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        super().setUp(**kwargs)
        self.enter_app_context()
        self.secret = self.app.config['ZENCODER_NOTIFICATIONS_SECRET']

    def test_missing_secret(self):
        self.post('/api/encoding/zencoder/notifications',
                  expected_status=401)

    def test_wrong_secret(self):
        self.post('/api/encoding/zencoder/notifications',
                  headers={'X-Zencoder-Notification-Secret': 'koro'},
                  expected_status=401)

    def test_good_secret_existing_file(self):
        self.ensure_file_exists(file_overrides={
            'processing': {'backend': 'zencoder',
                           'job_id': 'koro-007',
                           'status': 'processing'}
        })

        self.post('/api/encoding/zencoder/notifications',
                  json={'job': {'id': 'koro-007',
                                'state': 'done'},
                        'outputs': [{
                            'format': 'jpg',
                            'height': 1080,
                            'width': 2048,
                            'file_size_in_bytes': 15,
                            'md5_checksum': None,
                        }],
                        'input': {
                            'duration_in_ms': 5000,
                        }},
                  headers={'X-Zencoder-Notification-Secret': self.secret},
                  expected_status=204)

        # TODO: check that the file in MongoDB is actually updated properly.
