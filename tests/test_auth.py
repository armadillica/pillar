import datetime
import responses
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
