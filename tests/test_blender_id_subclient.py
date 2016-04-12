# -*- encoding: utf-8 -*-

import responses
import json

from bson import ObjectId

from common_test_class import AbstractPillarTest

TEST_FULL_NAME = u'врач Сергей'
TEST_EMAIL = 'jemoeder@example.com'
TEST_SUBCLIENT_TOKEN = 'my-subclient-token-for-pillar'
BLENDER_ID_TEST_USERID = 1896
BLENDER_ID_USER_RESPONSE = {'status': 'success',
                            'user': {'email': TEST_EMAIL, 'full_name': TEST_FULL_NAME}}


class BlenderIdSubclientTest(AbstractPillarTest):
    @responses.activate
    def test_store_scst_new_user(self):
        self._common_user_test(201)

    @responses.activate
    def test_store_scst_existing_user(self):
        # Make sure the user exists in our database.
        from application.utils.authentication import create_new_user
        with self.app.test_request_context():
            create_new_user(TEST_EMAIL, 'apekoppie', BLENDER_ID_TEST_USERID)

        self._common_user_test(200)

    def _common_user_test(self, expected_status_code):
        responses.add(responses.POST,
                      '%s/subclients/validate_token' % self.app.config['BLENDER_ID_ENDPOINT'],
                      json=BLENDER_ID_USER_RESPONSE,
                      status=200)

        resp = self.client.post('/blender_id/store_scst',
                                data={'user_id': BLENDER_ID_TEST_USERID,
                                      'scst': TEST_SUBCLIENT_TOKEN})
        self.assertEqual(expected_status_code, resp.status_code)

        user_info = json.loads(resp.data)  # {'status': 'success', 'subclient_user_id': '...'}
        self.assertEqual('success', user_info['status'])
        # Check that the user was correctly updated
        with self.app.test_request_context():
            users = self.app.data.driver.db['users']
            db_user = users.find_one(ObjectId(user_info['subclient_user_id']))
            self.assertIsNotNone(db_user, 'user %r not found' % user_info['subclient_user_id'])

            self.assertEqual(TEST_EMAIL, db_user['email'])
            self.assertEqual(TEST_FULL_NAME, db_user['full_name'])
            self.assertEqual(TEST_SUBCLIENT_TOKEN, db_user['auth'][0]['token'])
            self.assertEqual(str(BLENDER_ID_TEST_USERID), db_user['auth'][0]['user_id'])
            self.assertEqual('blender-id', db_user['auth'][0]['provider'])
