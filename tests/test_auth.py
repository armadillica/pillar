import base64
import httpretty

from common_test_class import AbstractPillarTest, TEST_EMAIL_USER, TEST_EMAIL_ADDRESS


def make_header(username, password=''):
    """Returns a Basic HTTP Authentication header value."""

    return 'basic ' + base64.b64encode('%s:%s' % (username, password))


class AuthenticationTests(AbstractPillarTest):
    def test_make_unique_username(self):
        from application.utils import authentication as auth

        with self.app.test_request_context():
            # This user shouldn't exist yet.
            self.assertEqual(TEST_EMAIL_USER, auth.make_unique_username(TEST_EMAIL_ADDRESS))

            # Add a user, then test again.
            auth.create_new_user(TEST_EMAIL_ADDRESS, TEST_EMAIL_USER, 'test1234')
            self.assertEqual('%s1' % TEST_EMAIL_USER, auth.make_unique_username(TEST_EMAIL_ADDRESS))

    @httpretty.activate
    def test_validate_token__not_logged_in(self):
        from application.utils import authentication as auth

        with self.app.test_request_context():
            self.assertFalse(auth.validate_token())

    @httpretty.activate
    def test_validate_token__unknown_token(self):
        """Test validating of invalid token, unknown both to us and Blender ID."""

        from application.utils import authentication as auth

        self.htp_blenderid_validate_unhappy()
        with self.app.test_request_context(headers={'Authorization': make_header('unknowntoken')}):
            self.assertFalse(auth.validate_token())

    @httpretty.activate
    def test_validate_token__unknown_but_valid_token(self):
        """Test validating of valid token, unknown to us but known to Blender ID."""

        from application.utils import authentication as auth

        self.htp_blenderid_validate_happy()
        with self.app.test_request_context(headers={'Authorization': make_header('knowntoken')}):
            self.assertTrue(auth.validate_token())
