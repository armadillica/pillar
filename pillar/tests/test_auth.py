import unittest
import os
import base64

TEST_EMAIL_USER = 'koro'
TEST_EMAIL_ADDRESS = '%s@testing.blender.org' % TEST_EMAIL_USER

os.environ['MONGO_DBNAME'] = 'unittest'
os.environ['EVE_SETTINGS'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'settings.py')


from application import app
from application.utils.authentication import make_unique_username, validate_token


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
            self.assertEqual(TEST_EMAIL_USER, make_unique_username(TEST_EMAIL_ADDRESS))

            # Add a user, then test again.
            user_data = {
                'full_name': 'Coro the Llama',
                'username': TEST_EMAIL_USER,
                'email': TEST_EMAIL_ADDRESS,
                'auth': [{
                    'provider': 'unit-test',
                    'user_id': 'test123',
                    'token': ''}],
                'settings': {
                    'email_communications': 0
                }
            }

            users.insert_one(user_data)
            try:
                self.assertIsNotNone(users.find_one({'username': TEST_EMAIL_USER}))
                self.assertEqual('%s1' % TEST_EMAIL_USER, make_unique_username(TEST_EMAIL_ADDRESS))
            finally:
                users.delete_many({'username': TEST_EMAIL_USER})

    def test_validate_token__not_logged_in(self):
        with app.test_request_context():
            self.assertFalse(validate_token())

    def test_validate_token__unknown_token(self):
        with app.test_request_context(headers={'Authorization': make_header('unknowntoken')}):
            self.assertFalse(validate_token())
