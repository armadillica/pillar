"""Test cases for the zencoder notifications."""
import json

from common_test_class import AbstractPillarTest


class ZencoderNotificationTest(AbstractPillarTest):

    def test_missing_secret(self):
        with self.app.test_request_context():
            resp = self.client.post('/encoding/zencoder/notifications')
        self.assertEqual(401, resp.status_code)

    def test_wrong_secret(self):
        with self.app.test_request_context():
            resp = self.client.post('/encoding/zencoder/notifications',
                                    headers={'X-Zencoder-Notification-Secret': 'koro'})
        self.assertEqual(401, resp.status_code)

    def test_good_secret_missing_file(self):
        with self.app.test_request_context():
            secret = self.app.config['ZENCODER_NOTIFICATIONS_SECRET']
            resp = self.client.post('/encoding/zencoder/notifications',
                                    data=json.dumps({'job': {'id': 'koro-007'}}),
                                    headers={'X-Zencoder-Notification-Secret': secret,
                                             'Content-Type': 'application/json'})
        self.assertEqual(404, resp.status_code)

    def test_good_secret_existing_file(self):
        self.ensure_file_exists(file_overrides={
            'processing': {'backend': 'zencoder',
                           'job_id': 'koro-007',
                           'status': 'processing'}
        })

        with self.app.test_request_context():
            secret = self.app.config['ZENCODER_NOTIFICATIONS_SECRET']
            resp = self.client.post('/encoding/zencoder/notifications',
                                    data=json.dumps({'job': {'id': 'koro-007',
                                                             'state': 'done'},
                                                     'outputs': [{
                                                         'format': 'jpg',
                                                         'width': 2048,
                                                         'file_size_in_bytes': 15,
                                                     }]}),
                                    headers={'X-Zencoder-Notification-Secret': secret,
                                             'Content-Type': 'application/json'})

        # TODO: check that the file in MongoDB is actually updated properly.
        self.assertEqual(200, resp.status_code)
