import unittest
import os
import base64

TEST_EMAIL_USER = 'koro'
TEST_EMAIL_ADDRESS = '%s@testing.blender.org' % TEST_EMAIL_USER

os.environ['MONGO_DBNAME'] = 'unittest'
os.environ['EVE_SETTINGS'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'settings.py')

from application import app
from application.utils import authentication as auth


def make_header(username, password=''):
    """Returns a Basic HTTP Authentication header value."""

    return 'basic ' + base64.b64encode('%s:%s' % (username, password))


class FlaskrTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()

    def tearDown(self):
        pass

    def test_make_unique_username(self):

        with app.test_request_context():
            # Delete the user we want to test for
            users = app.data.driver.db['users']
            users.delete_many({'username': TEST_EMAIL_USER})

            # This user shouldn't exist yet.
            self.assertEqual(TEST_EMAIL_USER, auth.make_unique_username(TEST_EMAIL_ADDRESS))

            # Add a user, then test again.
            auth.create_new_user(TEST_EMAIL_ADDRESS, TEST_EMAIL_USER, 'test1234')
            try:
                self.assertEqual('%s1' % TEST_EMAIL_USER, auth.make_unique_username(TEST_EMAIL_ADDRESS))
            finally:
                users.delete_many({'username': TEST_EMAIL_USER})

    def test_validate_token__not_logged_in(self):
        with app.test_request_context():
            self.assertFalse(auth.validate_token())

    def test_validate_token__unknown_token(self):
        with app.test_request_context(headers={'Authorization': make_header('unknowntoken')}):
            self.assertFalse(auth.validate_token())
