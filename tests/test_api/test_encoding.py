"""Test cases for the zencoder notifications."""
import dateutil.parser
from bson import ObjectId

from pillar.tests import AbstractPillarTest
from pillar.tests import common_test_data as ctd


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
        file_id, _ = self.ensure_file_exists(file_overrides={
            'processing': {'backend': 'zencoder',
                           'job_id': 'koro-007',
                           'status': 'processing'}
        })

        self.post('/api/encoding/zencoder/notifications',
                  json={'job': {'id': 'koro-007',
                                'state': 'finished'},
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

        db_file = self.app.db('files').find_one(file_id)
        self.assertEqual('complete', db_file['status'])
        self.assertEqual('finished', db_file['processing']['status'])

    def test_failed_job(self):
        file_id, _ = self.ensure_file_exists(file_overrides={
            'processing': {'backend': 'zencoder',
                           'job_id': 'koro-007',
                           'status': 'processing'}
        })

        self.post('/api/encoding/zencoder/notifications',
                  json={'job': {'id': 'koro-007',
                                'state': 'failed'},
                        'outputs': [{
                            'format': 'jpg',
                            'height': 1080,
                            'width': 2048,
                            'file_size_in_bytes': 15,
                            'md5_checksum': None,
                            'error': 'Lama support malfunctioning',
                            'url': 'http://example.com/file.mp4',
                        }],
                        'input': {
                            'duration_in_ms': 5000,
                        }},
                  headers={'X-Zencoder-Notification-Secret': self.secret})

        db_file = self.app.db('files').find_one(file_id)
        self.assertEqual('failed', db_file['status'])
        self.assertEqual('failed', db_file['processing']['status'])

    def test_failure_saving(self):
        # This document is intentionally created with non-existing project ID. As a result,
        # it cannot be saved any more with Eve.
        file_doc = {
            "_id": ObjectId("5a6751b33bea6a01fdfd59f0"),
            "name": "02a877a1d9da45509cdba97e283ef0bc.mkv",
            "filename": "4. pose-library-previews.mkv",
            "file_path": "02a877a1d9da45509cdba97e283ef0bc.mkv",
            "user": ctd.EXAMPLE_PROJECT_OWNER_ID,
            "backend": "gcs",
            "md5": "",
            "content_type": "video/x-matroska",
            "length": 39283494,
            "project": ObjectId('deadbeefcafef00dbeefcace'),
            "status": "processing",
            "length_aggregate_in_bytes": 45333852,
            "format": "x-matroska",
            "variations": [{
                "format": "mp4",
                "content_type": "video/mp4",
                "file_path": "02a877a1d9da45509cdba97e283ef0bc-1080p.mp4",
                "size": "1080p",
                "duration": 100,
                "width": 1920,
                "height": 1080,
                "length": 6050358,
                "md5": "",
                "link": "https://storage.googleapis.com/59d69c94f4/_%2F02-1080p.mp4"
            }],
            "processing": {
                "status": "processing",
                "job_id": "447043841",
                "backend": "zencoder"
            },
            "link_expires": dateutil.parser.parse("2018-01-27T06:24:31.827+0100"),
            "_updated": dateutil.parser.parse("2018-01-26T07:24:54.000+0100"),
            "_created": dateutil.parser.parse("2018-01-23T16:16:03.000+0100"),
            "_deleted": False,
            "_etag": "54f1d65326f4d856b740480dc52edefa96476d8a",
            "link": "https://storage.googleapis.com/59d69c94f4/_%2F02.mkv"
        }

        files_coll = self.app.db('files')
        files_coll.insert_one(file_doc)
        file_id = file_doc['_id']

        notif = {
            'job': {'created_at': '2018-01-23T15:16:17Z',
                    'id': 447043841,
                    'pass_through': None,
                    'state': 'finished',
                    'submitted_at': '2018-01-23T15:16:17Z',
                    'test': False,
                    'updated_at': '2018-01-23T15:16:42Z'},
            'outputs': [{'height': 1080,
                         'id': 1656104422,
                         'format': 'je moeder',
                         'url': 'gcs://59d69c94f488551661254569/_/02-mp4.mp4',
                         'width': 1920}]}

        self.post('/api/encoding/zencoder/notifications',
                  json=notif,
                  headers={'X-Zencoder-Notification-Secret': self.secret},
                  expected_status=500)

        db_file = files_coll.find_one(file_id)
        self.assertEqual('processing', db_file['status'])
        self.assertEqual('processing', db_file['processing']['status'])

    def test_actual_notification(self):
        """Test with actual file and notification documents."""
        self.ensure_project_exists()
        file_doc = {
            "_id": ObjectId("5a6751b33bea6a01fdfd59f0"),
            "name": "02a877a1d9da45509cdba97e283ef0bc.mkv",
            "filename": "4. pose-library-previews.mkv",
            "file_path": "02a877a1d9da45509cdba97e283ef0bc.mkv",
            "user": ctd.EXAMPLE_PROJECT_OWNER_ID,
            "backend": "gcs",
            "md5": "",
            "content_type": "video/x-matroska",
            "length": 39283494,
            "project": ctd.EXAMPLE_PROJECT_ID,
            "status": "processing",
            "length_aggregate_in_bytes": 45333852,
            "format": "x-matroska",
            "variations": [{
                "format": "mp4",
                "content_type": "video/mp4",
                "file_path": "02a877a1d9da45509cdba97e283ef0bc-1080p.mp4",
                "size": "1080p",
                "duration": 100,
                "width": 1920,
                "height": 1080,
                "length": 6050358,
                "md5": "",
                "link": "https://storage.googleapis.com/59d69c94f4/_%2F02-1080p.mp4"
            }],
            "processing": {
                "status": "processing",
                "job_id": "447043841",
                "backend": "zencoder"
            },
            "link_expires": dateutil.parser.parse("2018-01-27T06:24:31.827+0100"),
            "_updated": dateutil.parser.parse("2018-01-26T07:24:54.000+0100"),
            "_created": dateutil.parser.parse("2018-01-23T16:16:03.000+0100"),
            "_deleted": False,
            "_etag": "54f1d65326f4d856b740480dc52edefa96476d8a",
            "link": "https://storage.googleapis.com/59d69c94f4/_%2F02.mkv"
        }

        files_coll = self.app.db('files')
        files_coll.insert_one(file_doc)
        file_id = file_doc['_id']

        notif = {
            'input': {'audio_bitrate_in_kbps': None,
                      'audio_codec': None,
                      'audio_sample_rate': None,
                      'channels': None,
                      'duration_in_ms': 100840,
                      'file_size_in_bytes': 39283494,
                      'format': 'matroska',
                      'frame_rate': 25.0,
                      'height': 1080,
                      'id': 447014781,
                      'md5_checksum': None,
                      'state': 'finished',
                      'total_bitrate_in_kbps': None,
                      'video_bitrate_in_kbps': 3054,
                      'video_codec': 'h264',
                      'width': 1920},
            'job': {'created_at': '2018-01-23T15:16:17Z',
                    'id': 447043841,
                    'pass_through': None,
                    'state': 'finished',
                    'submitted_at': '2018-01-23T15:16:17Z',
                    'test': False,
                    'updated_at': '2018-01-23T15:16:42Z'},
            'outputs': [{'audio_bitrate_in_kbps': None,
                         'audio_codec': None,
                         'audio_sample_rate': None,
                         'channels': None,
                         'duration_in_ms': 100840,
                         'file_size_in_bytes': 6050358,
                         'format': 'mpeg4',
                         'fragment_duration_in_ms': None,
                         'frame_rate': 25.0,
                         'height': 1080,
                         'id': 1656104422,
                         'label': None,
                         'md5_checksum': None,
                         'rfc_6381_audio_codec': None,
                         'rfc_6381_video_codec': 'avc1.420028',
                         'state': 'finished',
                         'total_bitrate_in_kbps': 479,
                         'type': 'standard',
                         'url': 'gcs://59d69c94f488551661254569/_/02-mp4.mp4',
                         'video_bitrate_in_kbps': 479,
                         'video_codec': 'h264',
                         'width': 1920}]}

        self.post('/api/encoding/zencoder/notifications',
                  json=notif,
                  headers={'X-Zencoder-Notification-Secret': self.secret},
                  expected_status=204)

        db_file = files_coll.find_one(file_id)
        self.assertEqual('complete', db_file['status'])
        self.assertEqual('finished', db_file['processing']['status'])
