# -*- encoding: utf-8 -*-

import copy
import datetime
import json

import pillar.tests.common_test_data as ctd
import responses
from bson import tz_util, ObjectId
from pillar.tests import AbstractPillarTest, TEST_EMAIL_USER, TEST_EMAIL_ADDRESS
from pillar.tests.common_test_data import EXAMPLE_NODE
from werkzeug.exceptions import Forbidden

PUBLIC_USER_FIELDS = {'full_name', 'email', 'username'}

# Use the example project with some additional permissions for these tests.
EXAMPLE_PROJECT = copy.deepcopy(ctd.EXAMPLE_PROJECT)

_texture_nt = next(nt for nt in EXAMPLE_PROJECT['node_types']
                   if nt['name'] == 'texture')
_texture_nt['permissions'] = {'groups': [
    {'group': ObjectId('5596e975ea893b269af85c0f'), 'methods': ['GET']},
    {'group': ObjectId('564733b56dcaf85da2faee8a'), 'methods': ['GET']}
]}

_asset_nt = next(nt for nt in EXAMPLE_PROJECT['node_types']
                 if nt['name'] == 'asset')
_asset_nt['permissions'] = {'groups': [
    {'group': ObjectId('5596e975ea893b269af85c0f'), 'methods': ['DELETE', 'GET']},
    {'group': ObjectId('564733b56dcaf85da2faee8a'), 'methods': ['GET']}
]}


class AuthenticationTests(AbstractPillarTest):
    def test_make_unique_username(self):
        from pillar.api.utils import authentication as auth

        with self.app.test_request_context():
            # This user shouldn't exist yet.
            self.assertEqual(TEST_EMAIL_USER, auth.make_unique_username(TEST_EMAIL_ADDRESS))

            # Add a user, then test again.
            auth.create_new_user(TEST_EMAIL_ADDRESS, TEST_EMAIL_USER, 'test1234')
            self.assertEqual('%s1' % TEST_EMAIL_USER, auth.make_unique_username(TEST_EMAIL_ADDRESS))

    @responses.activate
    def test_validate_token__not_logged_in(self):
        from pillar.api.utils import authentication as auth

        with self.app.test_request_context():
            self.assertFalse(auth.validate_token())

    @responses.activate
    def test_validate_token__unknown_token(self):
        """Test validating of invalid token, unknown both to us and Blender ID."""

        from pillar.api.utils import authentication as auth

        self.mock_blenderid_validate_unhappy()
        with self.app.test_request_context(
                headers={'Authorization': self.make_header('unknowntoken')}):
            self.assertFalse(auth.validate_token())

    @responses.activate
    def test_validate_token__unknown_but_valid_token(self):
        """Test validating of valid token, unknown to us but known to Blender ID."""

        from pillar.api.utils import authentication as auth

        self.mock_blenderid_validate_happy()
        with self.app.test_request_context(
                headers={'Authorization': self.make_header('knowntoken')}):
            self.assertTrue(auth.validate_token())

    @responses.activate
    def test_find_token(self):
        """Test finding of various tokens."""

        from pillar.api.utils import authentication as auth

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

        from pillar.api.utils import authentication as auth
        from pillar.api.utils import PillarJSONEncoder, remove_private_keys

        user_id = self.create_user(roles=['subscriber'])

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
        resp = self.client.post('/api/users/%s' % user_id,
                                data=json.dumps(updated_fields, cls=PillarJSONEncoder),
                                headers={'Authorization': self.make_header('nonexpired-main'),
                                         'Content-Type': 'application/json'})
        self.assertEqual(405, resp.status_code)

        # PUT and PATCH should not be allowed.
        resp = self.client.put('/api/users/%s' % user_id,
                               data=json.dumps(updated_fields, cls=PillarJSONEncoder),
                               headers={'Authorization': self.make_header('nonexpired-main'),
                                        'Content-Type': 'application/json'})
        self.assertEqual(403, resp.status_code)

        updated_fields = {'roles': ['admin', 'subscriber', 'demo']}
        resp = self.client.patch('/api/users/%s' % user_id,
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

            self.assertEqual(['subscriber'], db_user['roles'])

    def test_token_expiry(self):
        """Expired tokens should be deleted from the database."""

        # Insert long-expired, almost-expired and not-expired token.
        user_id = self.create_user()
        now = datetime.datetime.now(tz_util.utc)

        with self.app.test_request_context():
            from pillar.api.utils import authentication as auth

            auth.store_token(user_id, 'long-expired',
                             now - datetime.timedelta(days=365), None)
            auth.store_token(user_id, 'short-expired',
                             now - datetime.timedelta(seconds=5), None)
            auth.store_token(user_id, 'not-expired',
                             now + datetime.timedelta(days=1), None)

            # Validation should clean up old tokens.
            auth.validate_this_token('je', 'moeder')

            token_coll = self.app.data.driver.db['tokens']
            self.assertEqual({'short-expired', 'not-expired'},
                             {item['token'] for item in token_coll.find()})


class UserListTests(AbstractPillarTest):
    """Security-related tests."""

    def setUp(self, **kwargs):
        super(UserListTests, self).setUp()

        self.create_user(roles=['subscriber'], user_id='123456789abc123456789abc')
        self.create_user(roles=['admin'], user_id='223456789abc123456789abc')
        self.create_user(roles=['subscriber'], user_id='323456789abc123456789abc')

        self.create_valid_auth_token('123456789abc123456789abc', 'token')
        self.create_valid_auth_token('223456789abc123456789abc', 'admin-token')
        self.create_valid_auth_token('323456789abc123456789abc', 'other-token')

    def test_list_all_users_anonymous(self):
        # Listing all users should be forbidden
        resp = self.client.get('/api/users')
        self.assertEqual(403, resp.status_code)

    def test_list_all_users_subscriber(self):
        # Regular access should result in only your own info.
        resp = self.client.get('/api/users', headers={'Authorization': self.make_header('token')})
        users = json.loads(resp.data)

        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, users['_meta']['total'])

        # The 'auth' section should be removed.
        user_info = users['_items'][0]
        self.assertNotIn('auth', user_info)

    def test_list_all_users_admin(self):
        # Admin access should result in all users
        resp = self.client.get('/api/users', headers={'Authorization': self.make_header('admin-token')})
        users = json.loads(resp.data)

        self.assertEqual(200, resp.status_code)
        self.assertEqual(3, users['_meta']['total'])

        # The 'auth' section should be removed.
        for user_info in users['_items']:
            self.assertNotIn('auth', user_info)

    def test_list_all_users_admin_explicit_projection(self):
        # Admin access should result in all users
        projection = json.dumps({'auth': 1})
        resp = self.client.get('/api/users?projection=%s' % projection,
                               headers={'Authorization': self.make_header('admin-token')})
        users = json.loads(resp.data)

        self.assertEqual(200, resp.status_code)
        self.assertEqual(3, users['_meta']['total'])

        # The 'auth' section should be removed.
        for user_info in users['_items']:
            self.assertNotIn('auth', user_info)

    def test_user_anonymous(self):
        from pillar.api.utils import remove_private_keys

        # Getting a user should be limited to certain fields
        resp = self.client.get('/api/users/123456789abc123456789abc')
        self.assertEqual(200, resp.status_code)

        user_info = json.loads(resp.data)
        regular_info = remove_private_keys(user_info)
        self.assertEqual(PUBLIC_USER_FIELDS, set(regular_info.keys()))

    def test_own_user_subscriber(self):
        # Regular access should result in only your own info.
        resp = self.client.get('/api/users/123456789abc123456789abc',
                               headers={'Authorization': self.make_header('token')})
        user_info = json.loads(resp.data)

        self.assertEqual(200, resp.status_code)
        self.assertNotIn('auth', user_info)

    def test_own_user_subscriber_explicit_projection(self):
        # With a custom projection requesting the auth list
        projection = json.dumps({'auth': 1})
        resp = self.client.get('/api/users/%s?projection=%s' % ('123456789abc123456789abc', projection),
                               headers={'Authorization': self.make_header('token')})
        user_info = json.loads(resp.data)

        self.assertEqual(200, resp.status_code)
        self.assertNotIn('auth', user_info)

    def test_other_user_subscriber(self):
        from pillar.api.utils import remove_private_keys

        # Requesting another user should be limited to full name and email.
        resp = self.client.get('/api/users/%s' % '223456789abc123456789abc',
                               headers={'Authorization': self.make_header('token')})
        user_info = json.loads(resp.data)

        self.assertEqual(200, resp.status_code)
        self.assertNotIn('auth', user_info)

        regular_info = remove_private_keys(user_info)
        self.assertEqual(PUBLIC_USER_FIELDS, set(regular_info.keys()))

    def test_put_user(self):
        from pillar.api.utils import remove_private_keys

        # PUTting a user should work, and not mess up the auth field.
        resp = self.client.get('/api/users/123456789abc123456789abc',
                               headers={'Authorization': self.make_header('token')})
        user_info = json.loads(resp.data)
        put_user = remove_private_keys(user_info)

        resp = self.client.put('/api/users/123456789abc123456789abc',
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
        from pillar.api.utils import remove_private_keys

        # PUTting the user as another user should fail.
        resp = self.client.get('/api/users/123456789abc123456789abc',
                               headers={'Authorization': self.make_header('token')})
        user_info = json.loads(resp.data)
        put_user = remove_private_keys(user_info)

        resp = self.client.put('/api/users/123456789abc123456789abc',
                               headers={'Authorization': self.make_header('other-token'),
                                        'Content-Type': 'application/json',
                                        'If-Match': user_info['_etag']},
                               data=json.dumps(put_user))
        self.assertEqual(403, resp.status_code, resp.data)

    def test_put_admin(self):
        from pillar.api.utils import remove_private_keys

        # PUTting a user should work, and not mess up the auth field.
        resp = self.client.get('/api/users/123456789abc123456789abc',
                               headers={'Authorization': self.make_header('token')})
        user_info = json.loads(resp.data)
        put_user = remove_private_keys(user_info)

        resp = self.client.put('/api/users/123456789abc123456789abc',
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
            'full_name': 'คนรักของผัดไทย',
            'email': TEST_EMAIL_ADDRESS,
        }

        resp = self.client.post('/api/users',
                                headers={'Authorization': self.make_header('token'),
                                         'Content-Type': 'application/json'},
                                data=json.dumps(post_user))
        self.assertEqual(405, resp.status_code, resp.data)

        resp = self.client.post('/api/users',
                                headers={'Authorization': self.make_header('admin-token'),
                                         'Content-Type': 'application/json'},
                                data=json.dumps(post_user))
        self.assertEqual(405, resp.status_code, resp.data)

    def test_delete(self):
        """DELETING a user should fail for subscribers and admins alike."""

        resp = self.client.delete('/api/users/323456789abc123456789abc',
                                  headers={'Authorization': self.make_header('token')})
        self.assertEqual(405, resp.status_code, resp.data)

        resp = self.client.delete('/api/users/323456789abc123456789abc',
                                  headers={'Authorization': self.make_header('admin-token')})
        self.assertEqual(405, resp.status_code, resp.data)


class PermissionComputationTest(AbstractPillarTest):
    maxDiff = None

    def test_merge_permissions(self):
        from pillar.api.utils.authorization import merge_permissions

        with self.app.test_request_context():
            self.assertEqual({}, merge_permissions())
            self.assertEqual({}, merge_permissions({}))
            self.assertEqual({}, merge_permissions({}, {}, {}))

            # Merge one level deep
            self.assertEqual(
                {},
                merge_permissions({'users': []}, {'groups': []}, {'world': []}))
            self.assertEqual(
                {'users': [{'user': 'micak', 'methods': ['GET', 'POST', 'PUT']}],
                 'groups': [{'group': 'manatees', 'methods': ['DELETE', 'GET']}],
                 'world': ['GET']},
                merge_permissions(
                    {'users': [{'user': 'micak', 'methods': ['GET', 'POST', 'PUT']}]},
                    {'groups': [{'group': 'manatees', 'methods': ['DELETE', 'GET']}]},
                    {'world': ['GET']}))

            # Merge two levels deep.
            self.assertEqual(
                {'users': [{'user': 'micak', 'methods': ['GET', 'POST', 'PUT']}],
                 'groups': [{'group': 'lions', 'methods': ['GET']},
                            {'group': 'manatees', 'methods': ['GET', 'POST', 'PUT']}],
                 'world': ['GET']},
                merge_permissions(
                    {'users': [{'user': 'micak', 'methods': ['GET', 'PUT', 'POST']}],
                     'groups': [{'group': 'lions', 'methods': ['GET']}]},
                    {'groups': [{'group': 'manatees', 'methods': ['GET', 'PUT', 'POST']}]},
                    {'world': ['GET']}))

            # Merge three levels deep
            self.assertEqual(
                {'users': [{'user': 'micak', 'methods': ['DELETE', 'GET', 'POST', 'PUT']}],
                 'groups': [{'group': 'lions', 'methods': ['GET', 'PUT', 'SCRATCH']},
                            {'group': 'manatees', 'methods': ['GET', 'POST', 'PUT']}],
                 'world': ['GET']},
                merge_permissions(
                    {'users': [{'user': 'micak', 'methods': ['GET', 'PUT', 'POST']}],
                     'groups': [{'group': 'lions', 'methods': ['GET']},
                                {'group': 'manatees', 'methods': ['GET', 'PUT', 'POST']}],
                     'world': ['GET']},
                    {'users': [{'user': 'micak', 'methods': ['DELETE']}],
                     'groups': [{'group': 'lions', 'methods': ['GET', 'PUT', 'SCRATCH']}],
                     }
                ))

    def sort(self, permissions):
        """Returns a sorted copy of the permissions."""

        from pillar.api.utils.authorization import merge_permissions
        return merge_permissions(permissions, {})

    def test_effective_permissions(self):
        from pillar.api.utils.authorization import compute_aggr_permissions

        with self.app.test_request_context():
            # Test project permissions.
            self.assertEqual(
                {
                    'groups': [{'group': ObjectId('5596e975ea893b269af85c0e'),
                                 'methods': ['DELETE', 'GET', 'POST', 'PUT']}],
                    'world': ['GET']
                },
                self.sort(compute_aggr_permissions('projects', EXAMPLE_PROJECT, None)))

            # Test node type permissions.
            self.assertEqual(
                {
                    'groups': [{'group': ObjectId('5596e975ea893b269af85c0e'),
                                 'methods': ['DELETE', 'GET', 'POST', 'PUT']},
                                {'group': ObjectId('5596e975ea893b269af85c0f'),
                                 'methods': ['GET']},
                                {'group': ObjectId('564733b56dcaf85da2faee8a'),
                                 'methods': ['GET']}],
                    'world': ['GET']
                },
                self.sort(compute_aggr_permissions('projects', EXAMPLE_PROJECT, 'texture')))

        with self.app.test_request_context():
            # Test node permissions with non-existing project.
            node = copy.deepcopy(EXAMPLE_NODE)
            self.assertRaises(Forbidden, compute_aggr_permissions, 'nodes', node, None)

        with self.app.test_request_context():
            # Test node permissions without embedded project.
            self.ensure_project_exists(project_overrides=EXAMPLE_PROJECT)
            self.assertEqual(
                {'groups': [{'group': ObjectId('5596e975ea893b269af85c0e'),
                              'methods': ['DELETE', 'GET', 'POST', 'PUT']},
                             {'group': ObjectId('5596e975ea893b269af85c0f'),
                              'methods': ['DELETE', 'GET']},
                             {'group': ObjectId('564733b56dcaf85da2faee8a'),
                              'methods': ['GET']}],
                 'world': ['GET']},
                self.sort(compute_aggr_permissions('nodes', node, None)))

        with self.app.test_request_context():
            # Test node permissions with embedded project.
            node = copy.deepcopy(EXAMPLE_NODE)
            node['project'] = EXAMPLE_PROJECT
            self.assertEqual(
                {'groups': [{'group': ObjectId('5596e975ea893b269af85c0e'),
                              'methods': ['DELETE', 'GET', 'POST', 'PUT']},
                             {'group': ObjectId('5596e975ea893b269af85c0f'),
                              'methods': ['DELETE', 'GET']},
                             {'group': ObjectId('564733b56dcaf85da2faee8a'),
                              'methods': ['GET']}],
                 'world': ['GET']},
                self.sort(compute_aggr_permissions('nodes', node, None)))


class RequireRolesTest(AbstractPillarTest):
    def test_no_roles_required(self):
        from flask import g
        from pillar.api.utils.authorization import require_login

        called = [False]

        @require_login()
        def call_me():
            called[0] = True

        with self.app.test_request_context():
            g.current_user = {'user_id': ObjectId(24 * 'a'),
                              'roles': ['succubus']}
            call_me()

        self.assertTrue(called[0])

    def test_some_roles_required(self):
        from flask import g
        from pillar.api.utils.authorization import require_login

        called = [False]

        @require_login(require_roles={'admin'})
        def call_me():
            called[0] = True

        with self.app.test_request_context():
            g.current_user = {'user_id': ObjectId(24 * 'a'),
                              'roles': ['succubus']}
            self.assertRaises(Forbidden, call_me)
        self.assertFalse(called[0])

        with self.app.test_request_context():
            g.current_user = {'user_id': ObjectId(24 * 'a'),
                              'roles': ['admin']}
            call_me()
        self.assertTrue(called[0])

    def test_all_roles_required(self):
        from flask import g
        from pillar.api.utils.authorization import require_login

        called = [False]

        @require_login(require_roles={'service', 'badger'},
                       require_all=True)
        def call_me():
            called[0] = True

        with self.app.test_request_context():
            g.current_user = {'user_id': ObjectId(24 * 'a'),
                              'roles': ['admin']}
            self.assertRaises(Forbidden, call_me)
        self.assertFalse(called[0])

        with self.app.test_request_context():
            g.current_user = {'user_id': ObjectId(24 * 'a'),
                              'roles': ['service']}
            self.assertRaises(Forbidden, call_me)
        self.assertFalse(called[0])

        with self.app.test_request_context():
            g.current_user = {'user_id': ObjectId(24 * 'a'),
                              'roles': ['badger']}
            self.assertRaises(Forbidden, call_me)
        self.assertFalse(called[0])

        with self.app.test_request_context():
            g.current_user = {'user_id': ObjectId(24 * 'a'),
                              'roles': ['service', 'badger']}
            call_me()
        self.assertTrue(called[0])

    def test_user_has_role(self):
        from pillar.api.utils.authorization import user_has_role

        with self.app.test_request_context():
            self.assertTrue(user_has_role('subscriber', {'roles': ['aap', 'noot', 'subscriber']}))
            self.assertTrue(user_has_role('subscriber', {'roles': ['aap', 'subscriber']}))
            self.assertFalse(user_has_role('admin', {'roles': ['aap', 'noot', 'subscriber']}))
            self.assertFalse(user_has_role('admin', {'roles': []}))
            self.assertFalse(user_has_role('admin', {'roles': None}))
            self.assertFalse(user_has_role('admin', {}))
