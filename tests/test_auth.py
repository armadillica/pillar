# -*- encoding: utf-8 -*-

import datetime
import responses
import json
from bson import tz_util, ObjectId

from common_test_class import AbstractPillarTest, TEST_EMAIL_USER, TEST_EMAIL_ADDRESS

PUBLIC_USER_FIELDS = {'full_name', 'email'}


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
        self.assertEqual(405, resp.status_code)

        # After all of this, the roles should be the same.
        with self.app.test_request_context(
                headers={'Authorization': self.make_header('nonexpired-main')}):
            self.assertTrue(auth.validate_token())

            users = self.app.data.driver.db['users']
            db_user = users.find_one(user_id)

            self.assertEqual([u'subscriber'], db_user['roles'])


class UserListTests(AbstractPillarTest):
    """Security-related tests."""

    def setUp(self, **kwargs):
        super(UserListTests, self).setUp()

        self.create_user(roles=[u'subscriber'], user_id='123456789abc123456789abc')
        self.create_user(roles=[u'admin'], user_id='223456789abc123456789abc')
        self.create_user(roles=[u'subscriber'], user_id='323456789abc123456789abc')

        self.create_valid_auth_token('123456789abc123456789abc', 'token')
        self.create_valid_auth_token('223456789abc123456789abc', 'admin-token')
        self.create_valid_auth_token('323456789abc123456789abc', 'other-token')

    def test_list_all_users_anonymous(self):
        # Listing all users should be forbidden
        resp = self.client.get('/users')
        self.assertEqual(403, resp.status_code)

    def test_list_all_users_subscriber(self):
        # Regular access should result in only your own info.
        resp = self.client.get('/users', headers={'Authorization': self.make_header('token')})
        users = json.loads(resp.data)

        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, users['_meta']['total'])

        # The 'auth' section should be removed.
        user_info = users['_items'][0]
        self.assertNotIn('auth', user_info)

    def test_list_all_users_admin(self):
        # Admin access should result in all users
        resp = self.client.get('/users', headers={'Authorization': self.make_header('admin-token')})
        users = json.loads(resp.data)

        self.assertEqual(200, resp.status_code)
        self.assertEqual(3, users['_meta']['total'])

        # The 'auth' section should be removed.
        for user_info in users['_items']:
            self.assertNotIn('auth', user_info)

    def test_list_all_users_admin_explicit_projection(self):
        # Admin access should result in all users
        projection = json.dumps({'auth': 1})
        resp = self.client.get('/users?projection=%s' % projection,
                               headers={'Authorization': self.make_header('admin-token')})
        users = json.loads(resp.data)

        self.assertEqual(200, resp.status_code)
        self.assertEqual(3, users['_meta']['total'])

        # The 'auth' section should be removed.
        for user_info in users['_items']:
            self.assertNotIn('auth', user_info)

    def test_user_anonymous(self):
        from application.utils import remove_private_keys

        # Getting a user should be limited to certain fields
        resp = self.client.get('/users/123456789abc123456789abc')
        self.assertEqual(200, resp.status_code)

        user_info = json.loads(resp.data)
        regular_info = remove_private_keys(user_info)
        self.assertEqual(PUBLIC_USER_FIELDS, set(regular_info.keys()))

    def test_own_user_subscriber(self):
        # Regular access should result in only your own info.
        resp = self.client.get('/users/123456789abc123456789abc',
                               headers={'Authorization': self.make_header('token')})
        user_info = json.loads(resp.data)

        self.assertEqual(200, resp.status_code)
        self.assertNotIn('auth', user_info)

    def test_own_user_subscriber_explicit_projection(self):
        # With a custom projection requesting the auth list
        projection = json.dumps({'auth': 1})
        resp = self.client.get('/users/%s?projection=%s' % ('123456789abc123456789abc', projection),
                               headers={'Authorization': self.make_header('token')})
        user_info = json.loads(resp.data)

        self.assertEqual(200, resp.status_code)
        self.assertNotIn('auth', user_info)

    def test_other_user_subscriber(self):
        from application.utils import remove_private_keys

        # Requesting another user should be limited to full name and email.
        resp = self.client.get('/users/%s' % '223456789abc123456789abc',
                               headers={'Authorization': self.make_header('token')})
        user_info = json.loads(resp.data)

        self.assertEqual(200, resp.status_code)
        self.assertNotIn('auth', user_info)

        regular_info = remove_private_keys(user_info)
        self.assertEqual(PUBLIC_USER_FIELDS, set(regular_info.keys()))

    def test_put_user(self):
        from application.utils import remove_private_keys

        # PUTting a user should work, and not mess up the auth field.
        resp = self.client.get('/users/123456789abc123456789abc',
                               headers={'Authorization': self.make_header('token')})
        user_info = json.loads(resp.data)
        put_user = remove_private_keys(user_info)

        resp = self.client.put('/users/123456789abc123456789abc',
                               headers={'Authorization': self.make_header('token'),
                                        'Content-Type': 'application/json',
                                        'If-Match': user_info['_etag']},
                               data=json.dumps(put_user))
        self.assertEqual(200, resp.status_code, resp.data)

        # Get directly from MongoDB, Eve blocks access to the auth field.
        with self.app.test_request_context():
            users = self.app.data.driver.db['users']
            db_user = users.find_one(ObjectId('123456789abc123456789abc'))
            self.assertIn('auth', db_user)

    def test_put_other_user(self):
        from application.utils import remove_private_keys

        # PUTting the user as another user should fail.
        resp = self.client.get('/users/123456789abc123456789abc',
                               headers={'Authorization': self.make_header('token')})
        user_info = json.loads(resp.data)
        put_user = remove_private_keys(user_info)

        resp = self.client.put('/users/123456789abc123456789abc',
                               headers={'Authorization': self.make_header('other-token'),
                                        'Content-Type': 'application/json',
                                        'If-Match': user_info['_etag']},
                               data=json.dumps(put_user))
        self.assertEqual(403, resp.status_code, resp.data)

    def test_put_admin(self):
        from application.utils import remove_private_keys

        # PUTting a user should work, and not mess up the auth field.
        resp = self.client.get('/users/123456789abc123456789abc',
                               headers={'Authorization': self.make_header('token')})
        user_info = json.loads(resp.data)
        put_user = remove_private_keys(user_info)

        resp = self.client.put('/users/123456789abc123456789abc',
                               headers={'Authorization': self.make_header('admin-token'),
                                        'Content-Type': 'application/json',
                                        'If-Match': user_info['_etag']},
                               data=json.dumps(put_user))
        self.assertEqual(200, resp.status_code, resp.data)

        # Get directly from MongoDB, Eve blocks access to the auth field.
        with self.app.test_request_context():
            users = self.app.data.driver.db['users']
            db_user = users.find_one(ObjectId('123456789abc123456789abc'))
            self.assertIn('auth', db_user)

    def test_post(self):
        """POSTing to /users should fail for subscribers and admins alike."""

        post_user = {
            'username': 'unique-user-name',
            'groups': [],
            'roles': ['subscriber'],
            'settings': {'email_communications': 1},
            'auth': [],
            'full_name': u'คนรักของผัดไทย',
            'email': TEST_EMAIL_ADDRESS,
        }

        resp = self.client.post('/users',
                                headers={'Authorization': self.make_header('token'),
                                         'Content-Type': 'application/json'},
                                data=json.dumps(post_user))
        self.assertEqual(405, resp.status_code, resp.data)

        resp = self.client.post('/users',
                                headers={'Authorization': self.make_header('admin-token'),
                                         'Content-Type': 'application/json'},
                                data=json.dumps(post_user))
        self.assertEqual(405, resp.status_code, resp.data)

    def test_delete(self):
        """DELETING a user should fail for subscribers and admins alike."""

        resp = self.client.delete('/users/323456789abc123456789abc',
                                  headers={'Authorization': self.make_header('token')})
        self.assertEqual(405, resp.status_code, resp.data)

        resp = self.client.delete('/users/323456789abc123456789abc',
                                  headers={'Authorization': self.make_header('admin-token')})
        self.assertEqual(405, resp.status_code, resp.data)
