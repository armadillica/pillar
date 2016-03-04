import unittest
import os
import base64
import httpretty
import json

BLENDER_ID_ENDPOINT = 'http://127.0.0.1:8001'  # nonexistant server, no trailing slash!
TEST_EMAIL_USER = 'koro'
TEST_EMAIL_ADDRESS = '%s@testing.blender.org' % TEST_EMAIL_USER

os.environ['BLENDER_ID_ENDPOINT'] = BLENDER_ID_ENDPOINT
os.environ['MONGO_DBNAME'] = 'unittest'
os.environ['EVE_SETTINGS'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'settings.py')

from application import app
from application.utils import authentication as auth


def make_header(username, password=''):
    """Returns a Basic HTTP Authentication header value."""

    return 'basic ' + base64.b64encode('%s:%s' % (username, password))


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        with app.test_request_context():
            self.delete_test_data()

    def tearDown(self):
        with app.test_request_context():
            self.delete_test_data()

    def test_make_unique_username(self):

        with app.test_request_context():
            # This user shouldn't exist yet.
            self.assertEqual(TEST_EMAIL_USER, auth.make_unique_username(TEST_EMAIL_ADDRESS))

            # Add a user, then test again.
            auth.create_new_user(TEST_EMAIL_ADDRESS, TEST_EMAIL_USER, 'test1234')
            self.assertEqual('%s1' % TEST_EMAIL_USER, auth.make_unique_username(TEST_EMAIL_ADDRESS))

    def test_validate_token__not_logged_in(self):
        with app.test_request_context():
            self.assertFalse(auth.validate_token())

    def delete_test_data(self):
        app.data.driver.db.drop_collection('users')
        app.data.driver.db.drop_collection('tokens')

    def blenderid_validate_unhappy(self):
        """Sets up HTTPretty to mock unhappy validation flow."""

        httpretty.register_uri(httpretty.POST,
                               '%s/u/validate_token' % BLENDER_ID_ENDPOINT,
                               body=json.dumps({'data': {'token': 'Token is invalid'}, 'status': 'fail'}),
                               content_type="application/json")

    def blenderid_validate_happy(self):
        """Sets up HTTPretty to mock happy validation flow."""

        httpretty.register_uri(httpretty.POST,
                               '%s/u/validate_token' % BLENDER_ID_ENDPOINT,
                               body=json.dumps({'data': {'user': {'email': TEST_EMAIL_ADDRESS, 'id': 5123}},
                                                'status': 'success'}),
                               content_type="application/json")

    @httpretty.activate
    def test_validate_token__unknown_token(self):
        """Test validating of invalid token, unknown both to us and Blender ID."""

        self.blenderid_validate_unhappy()
        with app.test_request_context(headers={'Authorization': make_header('unknowntoken')}):
            self.assertFalse(auth.validate_token())

    @httpretty.activate
    def test_validate_token__unknown_but_valid_token(self):
        """Test validating of valid token, unknown to us but known to Blender ID."""

        self.blenderid_validate_happy()
        with app.test_request_context(headers={'Authorization': make_header('knowntoken')}):
            self.assertTrue(auth.validate_token())
