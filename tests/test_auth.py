import datetime
import responses
import json
from bson import tz_util

from common_test_class import AbstractPillarTest, TEST_EMAIL_USER, TEST_EMAIL_ADDRESS


class AuthenticationTests(AbstractPillarTest):
    def test_make_unique_username(self):
        from application.utils import authentication as auth

        with self.app.test_request_context():
            # This user shouldn't exist yet.
            self.assertEqual(TEST_EMAIL_USER, auth.make_unique_username(TEST_EMAIL_ADDRESS))

            # Add a user, then test again.
            auth.create_new_user(TEST_EMAIL_ADDRESS, TEST_EMAIL_USER, 'test1234')
            self.assertEqual('%s1' % TEST_EMAIL_USER, auth.make_unique_username(TEST_EMAIL_ADDRESS))

    @responses.activate
    def test_validate_token__not_logged_in(self):
        from application.utils import authentication as auth

        with self.app.test_request_context():
            self.assertFalse(auth.validate_token())

    @responses.activate
    def test_validate_token__unknown_token(self):
        """Test validating of invalid token, unknown both to us and Blender ID."""

        from application.utils import authentication as auth

        self.mock_blenderid_validate_unhappy()
        with self.app.test_request_context(
                headers={'Authorization': self.make_header('unknowntoken')}):
            self.assertFalse(auth.validate_token())

    @responses.activate
    def test_validate_token__unknown_but_valid_token(self):
        """Test validating of valid token, unknown to us but known to Blender ID."""

        from application.utils import authentication as auth

        self.mock_blenderid_validate_happy()
        with self.app.test_request_context(
                headers={'Authorization': self.make_header('knowntoken')}):
            self.assertTrue(auth.validate_token())

    @responses.activate
    def test_find_token(self):
        """Test finding of various tokens."""

        from application.utils import authentication as auth

        user_id = self.create_user()

        now = datetime.datetime.now(tz_util.utc)
        future = now + datetime.timedelta(days=1)
        past = now - datetime.timedelta(days=1)
        subclient = self.app.config['BLENDER_ID_SUBCLIENT_ID']

        with self.app.test_request_context():
            auth.store_token(user_id, 'nonexpired-main', future, None)
            auth.store_token(user_id, 'nonexpired-sub', future, subclient)
            token3 = auth.store_token(user_id, 'expired-sub', past, subclient)

        with self.app.test_request_context(
                headers={'Authorization': self.make_header('nonexpired-main')}):
            self.assertTrue(auth.validate_token())

        with self.app.test_request_context(
                headers={'Authorization': self.make_header('nonexpired-main', subclient)}):
            self.assertFalse(auth.validate_token())

        with self.app.test_request_context(
                headers={'Authorization': self.make_header('nonexpired-sub')}):
            self.assertFalse(auth.validate_token())

        with self.app.test_request_context(
                headers={'Authorization': self.make_header('nonexpired-sub', subclient)}):
            self.assertTrue(auth.validate_token())

        with self.app.test_request_context(
                headers={'Authorization': self.make_header('expired-sub', subclient)}):
            self.assertFalse(auth.validate_token())

        self.mock_blenderid_validate_happy()
        with self.app.test_request_context(
                headers={'Authorization': self.make_header('expired-sub', subclient)}):
            self.assertTrue(auth.validate_token())

            # We now should be able to find a new token for this user.
            found_token = auth.find_token('expired-sub', subclient)
            self.assertIsNotNone(found_token)
            self.assertNotEqual(token3['_id'], found_token['_id'])

    @responses.activate
    def test_save_own_user(self):
        """Tests that a user can't change their own fields."""

        from application.utils import authentication as auth
        from application.utils import PillarJSONEncoder, remove_private_keys

        user_id = self.create_user(roles=[u'subscriber'])

        now = datetime.datetime.now(tz_util.utc)
        future = now + datetime.timedelta(days=1)

        with self.app.test_request_context():
            auth.store_token(user_id, 'nonexpired-main', future, None)

        with self.app.test_request_context(
                headers={'Authorization': self.make_header('nonexpired-main')}):
            self.assertTrue(auth.validate_token())

            users = self.app.data.driver.db['users']
            db_user = users.find_one(user_id)

        updated_fields = remove_private_keys(db_user)
        updated_fields['roles'] = ['admin', 'subscriber', 'demo']  # Try to elevate our roles.

        # POSTing updated info to a specific user URL is not allowed by Eve.
        resp = self.client.post('/users/%s' % user_id,
                                data=json.dumps(updated_fields, cls=PillarJSONEncoder),
                                headers={'Authorization': self.make_header('nonexpired-main'),
                                         'Content-Type': 'application/json'})
        self.assertEqual(405, resp.status_code)

        # POSTing with our _id to update shouldn't work either, as POST always creates new users.
        updated_fields_with_id = dict(_id=user_id, **updated_fields)
        resp = self.client.post('/users',
                                data=json.dumps(updated_fields_with_id, cls=PillarJSONEncoder),
                                headers={'Authorization': self.make_header('nonexpired-main'),
                                         'Content-Type': 'application/json'})
        self.assertEqual(422, resp.status_code)

        # PUT and PATCH should not be allowed.
        resp = self.client.put('/users/%s' % user_id,
                               data=json.dumps(updated_fields, cls=PillarJSONEncoder),
                               headers={'Authorization': self.make_header('nonexpired-main'),
                                        'Content-Type': 'application/json'})
        self.assertEqual(403, resp.status_code)

        updated_fields = {'roles': ['admin', 'subscriber', 'demo']}
        resp = self.client.patch('/users/%s' % user_id,
                                 data=json.dumps(updated_fields, cls=PillarJSONEncoder),
                                 headers={'Authorization': self.make_header('nonexpired-main'),
                                          'Content-Type': 'application/json'})
        self.assertEqual(403, resp.status_code)

        # After all of this, the roles should be the same.
        with self.app.test_request_context(
                headers={'Authorization': self.make_header('nonexpired-main')}):
            self.assertTrue(auth.validate_token())

            users = self.app.data.driver.db['users']
            db_user = users.find_one(user_id)

            self.assertEqual([u'subscriber'], db_user['roles'])
