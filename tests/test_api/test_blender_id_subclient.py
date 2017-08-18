# -*- encoding: utf-8 -*-

import json

import responses
from bson import ObjectId
from flask import g
from pillar.tests import (AbstractPillarTest, TEST_EMAIL_ADDRESS,
                          TEST_SUBCLIENT_TOKEN, TEST_EMAIL_USER, TEST_FULL_NAME)
from pillar.tests import common_test_data as ctd


class BlenderIdSubclientTest(AbstractPillarTest):
    @responses.activate
    def test_store_scst_new_user(self):
        self._common_user_test(201)

    @responses.activate
    def test_store_scst_new_user_without_full_name(self):

        responses.add(responses.POST,
                      '%s/u/validate_token' % self.app.config['BLENDER_ID_ENDPOINT'],
                      json={'status': 'success',
                            'user': {'email': TEST_EMAIL_ADDRESS,
                                     'full_name': None,
                                     'id': ctd.BLENDER_ID_TEST_USERID},
                            'token_expires': 'Mon, 1 Jan 2218 01:02:03 GMT'},
                      status=200)

        self._common_user_test(201,
                               expected_full_name=TEST_EMAIL_USER,
                               mock_happy_blender_id=False)

    @responses.activate
    def test_store_scst_existing_user(self):
        # Make sure the user exists in our database.
        from pillar.api.utils.authentication import create_new_user
        with self.app.test_request_context():
            create_new_user(TEST_EMAIL_ADDRESS, 'apekoppie', ctd.BLENDER_ID_TEST_USERID)

        self._common_user_test(200, expected_full_name='apekoppie')

    @responses.activate
    def test_store_multiple_tokens(self):
        scst1 = '%s-1' % TEST_SUBCLIENT_TOKEN
        scst2 = '%s-2' % TEST_SUBCLIENT_TOKEN
        db_user1 = self._common_user_test(201, scst=scst1)
        db_user2 = self._common_user_test(200, scst=scst2)
        self.assertEqual(db_user1['_id'], db_user2['_id'])

        # Now there should be two tokens.
        with self.app.test_request_context():
            tokens = self.app.data.driver.db['tokens']
            self.assertIsNotNone(tokens.find_one({'user': db_user1['_id'], 'token': scst1}))
            self.assertIsNotNone(tokens.find_one({'user': db_user1['_id'], 'token': scst2}))

        # There should still be only one auth element for blender-id in the user doc.
        self.assertEqual(1, len(db_user1['auth']))

    @responses.activate
    def test_authenticate_with_scst(self):
        # Make sure there is a user and SCST.
        db_user = self._common_user_test(201)

        # Make a call that's authenticated with the SCST
        from pillar.api.utils import authentication as auth

        subclient_id = self.app.config['BLENDER_ID_SUBCLIENT_ID']
        auth_header = self.make_header(TEST_SUBCLIENT_TOKEN, subclient_id)

        with self.app.test_request_context(headers={'Authorization': auth_header}):
            self.assertTrue(auth.validate_token())
            self.assertIsNotNone(g.current_user)
            self.assertEqual(db_user['_id'], g.current_user.user_id)

    def _common_user_test(self, expected_status_code, scst=TEST_SUBCLIENT_TOKEN,
                          expected_full_name=TEST_FULL_NAME,
                          mock_happy_blender_id=True):
        if mock_happy_blender_id:
            self.mock_blenderid_validate_happy()

        subclient_id = self.app.config['BLENDER_ID_SUBCLIENT_ID']
        resp = self.client.post('/api/blender_id/store_scst',
                                data={'user_id': ctd.BLENDER_ID_TEST_USERID,
                                      'subclient_id': subclient_id,
                                      'token': scst})
        self.assertEqual(expected_status_code, resp.status_code, resp.data)

        user_info = json.loads(resp.data)  # {'status': 'success', 'subclient_user_id': '...'}
        self.assertEqual('success', user_info['status'])

        with self.app.test_request_context():
            # Check that the user was correctly updated
            users = self.app.data.driver.db['users']
            db_user = users.find_one(ObjectId(user_info['subclient_user_id']))
            self.assertIsNotNone(db_user, 'user %r not found' % user_info['subclient_user_id'])

            self.assertEqual(TEST_EMAIL_ADDRESS, db_user['email'])
            self.assertEqual(expected_full_name, db_user['full_name'])
            # self.assertEqual(TEST_SUBCLIENT_TOKEN, db_user['auth'][0]['token'])
            self.assertEqual(str(ctd.BLENDER_ID_TEST_USERID), db_user['auth'][0]['user_id'])
            self.assertEqual('blender-id', db_user['auth'][0]['provider'])

            # Check that the token was succesfully stored.
            tokens = self.app.data.driver.db['tokens']
            db_token = tokens.find_one({'user': db_user['_id'],
                                        'token': scst})
            self.assertIsNotNone(db_token)

        return db_user
