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

        user_id = self.create_user(roles=['subscriber'], token='token')

        def fetch_user():
            with self.app.test_request_context():
                users_coll = self.app.db('users')
                return users_coll.find_one(user_id)

        db_user = fetch_user()
        updated_fields = remove_private_keys(db_user)
        updated_fields['roles'] = ['admin', 'subscriber', 'demo']  # Try to elevate our roles.

        # POSTing updated info to a specific user URL is not allowed by Eve.
        self.post('/api/users/%s' % user_id,
                  json=updated_fields,
                  auth_token='token',
                  expected_status=405)

        # PUT is allowed, but shouldn't change roles.
        self.put('/api/users/%s' % user_id,
                 json=updated_fields,
                 auth_token='token',
                 etag=db_user['_etag'])
        db_user = fetch_user()
        self.assertEqual(['subscriber'], db_user['roles'])

        # PATCH should not be allowed.
        updated_fields = {'roles': ['admin', 'subscriber', 'demo']}
        self.patch('/api/users/%s' % user_id,
                   json=updated_fields,
                   auth_token='token',
                   etag=db_user['_etag'],
                   expected_status=405)
        db_user = fetch_user()
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
        self.get('/api/users', expected_status=403)

    def test_list_all_users_subscriber(self):
        # Regular access should result in only your own info.
        users = self.get('/api/users', auth_token='token').json()
        self.assertEqual(1, users['_meta']['total'])

        # The 'auth' section should be removed.
        user_info = users['_items'][0]
        self.assertNotIn('auth', user_info)

    def test_list_all_users_admin(self):
        # Admin access should result in all users
        users = self.get('/api/users', auth_token='admin-token').json()
        self.assertEqual(3, users['_meta']['total'])

        # The 'auth' section should be removed.
        for user_info in users['_items']:
            self.assertNotIn('auth', user_info)

    def test_list_all_users_admin_explicit_projection(self):
        """Even admins shouldn't be able to GET auth info."""

        projection = json.dumps({'auth': 1})
        users = self.get(f'/api/users?projection={projection}', auth_token='admin-token').json()
        self.assertEqual(3, users['_meta']['total'])

        # The 'auth' section should be removed.
        for user_info in users['_items']:
            self.assertNotIn('auth', user_info)

    def test_user_anonymous(self):
        from pillar.api.utils import remove_private_keys

        # Getting a user should be limited to certain fields
        resp = self.get('/api/users/123456789abc123456789abc')

        user_info = json.loads(resp.data)
        regular_info = remove_private_keys(user_info)
        self.assertEqual(PUBLIC_USER_FIELDS, set(regular_info.keys()))

    def test_own_user_subscriber(self):
        # Regular access should result in only your own info.
        user_info = self.get('/api/users/123456789abc123456789abc', auth_token='token').json()
        self.assertNotIn('auth', user_info)

    def test_own_user_subscriber_explicit_projection(self):
        # With a custom projection requesting the auth list
        projection = json.dumps({'auth': 1})
        user_info = self.get(f'/api/users/123456789abc123456789abc?projection={projection}',
                             auth_token='token').json()
        self.assertNotIn('auth', user_info)

    def test_other_user_subscriber(self):
        from pillar.api.utils import remove_private_keys

        # Requesting another user should be limited to full name and email.
        user_info = self.get('/api/users/223456789abc123456789abc', auth_token='token').json()
        self.assertNotIn('auth', user_info)

        regular_info = remove_private_keys(user_info)
        self.assertEqual(PUBLIC_USER_FIELDS, set(regular_info.keys()))

    def test_put_user(self):
        from pillar.api.utils import remove_private_keys

        # PUTting a user should work, and not mess up the auth field.
        user_info = self.get('/api/users/123456789abc123456789abc', auth_token='token').json()
        self.assertNotIn('auth', user_info)

        put_user = remove_private_keys(user_info)
        self.put('/api/users/123456789abc123456789abc',
                 auth_token='token',
                 etag=user_info['_etag'],
                 json=put_user)

        # Get directly from MongoDB, Eve blocks access to the auth field.
        with self.app.test_request_context():
            users = self.app.data.driver.db['users']
            db_user = users.find_one(ObjectId('123456789abc123456789abc'))
            self.assertIn('auth', db_user)

    def test_put_user_restricted_fields(self):
        from pillar.api.utils import remove_private_keys

        group_ids = self.create_standard_groups()

        # A user should be able to change only some fields, but not all.
        user_info = self.get('/api/users/me', auth_token='token').json()

        # Alter all fields (except auth, another test already checks that that's uneditable).
        put_user = remove_private_keys(user_info)
        put_user['full_name'] = '¿new name?'
        put_user['username'] = 'üniék'
        put_user['email'] = 'new+email@example.com'
        put_user['roles'] = ['subscriber', 'demo', 'admin', 'service', 'flamenco_manager']
        put_user['groups'] = list(group_ids.keys())
        put_user['settings']['email_communications'] = 0
        put_user['service'] = {'flamenco_manager': {}}

        self.put(f'/api/users/{user_info["_id"]}',
                 json=put_user,
                 auth_token='token',
                 etag=user_info['_etag'])

        new_user_info = self.get('/api/users/me', auth_token='token').json()
        self.assertEqual(new_user_info['full_name'], put_user['full_name'])
        self.assertEqual(new_user_info['username'], put_user['username'])
        self.assertEqual(new_user_info['email'], put_user['email'])
        self.assertEqual(new_user_info['roles'], user_info['roles'])
        self.assertEqual(new_user_info['groups'], user_info['groups'])
        self.assertEqual(new_user_info['settings']['email_communications'],
                         put_user['settings']['email_communications'])
        self.assertNotIn('service', new_user_info)

    def test_put_other_user(self):
        from pillar.api.utils import remove_private_keys

        # PUTting the user as another user should fail.
        user_info = self.get('/api/users/123456789abc123456789abc', auth_token='token').json()
        put_user = remove_private_keys(user_info)

        self.put('/api/users/123456789abc123456789abc', auth_token='other-token',
                 json=put_user, etag=user_info['_etag'],
                 expected_status=403)

    def test_put_admin(self):
        from pillar.api.utils import remove_private_keys

        # PUTting a user should work, and not mess up the auth field.
        user_info = self.get('/api/users/123456789abc123456789abc', auth_token='token').json()
        put_user = remove_private_keys(user_info)

        self.put('/api/users/123456789abc123456789abc', auth_token='admin-token',
                 json=put_user, etag=user_info['_etag'])

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

        self.post('/api/users', auth_token='token', json=post_user, expected_status=405)
        self.post('/api/users', auth_token='admin-token', json=post_user, expected_status=405)

    def test_delete(self):
        """DELETING a user should fail for subscribers and admins alike."""

        self.delete('/api/users', auth_token='token', expected_status=405)
        self.delete('/api/users', auth_token='admin-token', expected_status=405)


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

    def test_delete_node(self):
        self.enter_app_context()

        proj_id, proj = self.ensure_project_exists()
        self.create_user(user_id=24 * 'a', roles={'subscriber'},
                         groups=[ctd.EXAMPLE_PROJECT_OWNER_ID])

        node = copy.deepcopy(ctd.EXAMPLE_NODE)
        node['project'] = proj_id
        node_id = self.create_node(node)

        # Try deletion by a user who is not part of the project.
        self.create_user(user_id=6 * 'dafe', roles={'subscriber'}, token='dafe-token')
        self.delete(f'/api/nodes/{node_id}',
                    auth_token='dafe-token',
                    etag=node['_etag'],
                    expected_status=403)

        found = self.app.db('nodes').find_one(node_id)
        self.assertFalse(found.get('_deleted', False))

    def test_delete_project(self):
        self.enter_app_context()

        proj_id, proj = self.ensure_project_exists()
        self.create_user(user_id=24 * 'a', roles={'subscriber'},
                         groups=[ctd.EXAMPLE_PROJECT_OWNER_ID])

        # Try deletion by a user who is not part of the project.
        self.create_user(user_id=6 * 'dafe', roles={'subscriber'}, token='dafe-token')
        self.delete(f'/api/projects/{proj_id}',
                    auth_token='dafe-token',
                    etag=proj['_etag'],
                    expected_status=403)

        found = self.app.db('projects').find_one(proj_id)
        self.assertIsNotNone(found)
        self.assertFalse(found.get('_deleted', False))


class RequireRolesTest(AbstractPillarTest):
    def test_no_roles_required(self):
        from pillar.api.utils.authorization import require_login

        called = [False]

        @require_login()
        def call_me():
            called[0] = True

        with self.app.test_request_context():
            self.login_api_as(ObjectId(24 * 'a'), roles=['succubus'])
            call_me()

        self.assertTrue(called[0])

    def test_some_roles_required(self):
        from pillar.api.utils.authorization import require_login

        called = [False]

        @require_login(require_roles={'admin'})
        def call_me():
            called[0] = True

        with self.app.test_request_context():
            self.login_api_as(ObjectId(24 * 'a'), ['succubus'])
            self.assertRaises(Forbidden, call_me)
        self.assertFalse(called[0])

        with self.app.test_request_context():
            self.login_api_as(ObjectId(24 * 'a'), ['admin'])
            call_me()
        self.assertTrue(called[0])

    def test_all_roles_required(self):
        from pillar.api.utils.authorization import require_login

        called = [False]

        @require_login(require_roles={'service', 'badger'},
                       require_all=True)
        def call_me():
            called[0] = True

        with self.app.test_request_context():
            self.login_api_as(ObjectId(24 * 'a'), ['admin'])
            self.assertRaises(Forbidden, call_me)
        self.assertFalse(called[0])

        with self.app.test_request_context():
            self.login_api_as(ObjectId(24 * 'a'), ['service'])
            self.assertRaises(Forbidden, call_me)
        self.assertFalse(called[0])

        with self.app.test_request_context():
            self.login_api_as(ObjectId(24 * 'a'), ['badger'])
            self.assertRaises(Forbidden, call_me)
        self.assertFalse(called[0])

        with self.app.test_request_context():
            self.login_api_as(ObjectId(24 * 'a'), ['service', 'badger'])
            call_me()
        self.assertTrue(called[0])

    def test_user_has_role(self):
        from pillar.api.utils.authorization import user_has_role

        def make_user(roles):
            return self.create_user_object(ObjectId(), roles=roles)

        with self.app.test_request_context():
            self.assertTrue(user_has_role('subscriber', make_user(['aap', 'noot', 'subscriber'])))
            self.assertTrue(user_has_role('subscriber', make_user(['aap', 'subscriber'])))
            self.assertFalse(user_has_role('admin', make_user(['aap', 'noot', 'subscriber'])))
            self.assertFalse(user_has_role('admin', make_user([])))
            self.assertFalse(user_has_role('admin', make_user(None)))
            self.assertFalse(user_has_role('admin', None))

    def test_cap_required(self):
        from pillar.api.utils.authorization import require_login

        called = [False]

        @require_login(require_cap='subscriber')
        def call_me():
            called[0] = True

        with self.app.test_request_context():
            self.login_api_as(ObjectId(24 * 'a'), ['succubus'])
            self.assertRaises(Forbidden, call_me)
        self.assertFalse(called[0])

        with self.app.test_request_context():
            self.login_api_as(ObjectId(24 * 'a'), ['admin'])
            call_me()
        self.assertTrue(called[0])

    def test_invalid_combinations(self):
        from pillar.api.utils.authorization import require_login

        with self.assertRaises(TypeError):
            require_login(require_roles=['abc', 'def'])

        with self.assertRaises(TypeError):
            require_login(require_cap={'multiple', 'caps'})

        with self.assertRaises(ValueError):
            require_login(require_roles=set(), require_all=True)

        with self.assertRaises(ValueError):
            require_login(require_roles={'admin'}, require_cap='hey')


class UserCreationTest(AbstractPillarTest):
    @responses.activate
    def test_create_by_auth(self):
        """Create user by authenticating against Blender ID."""

        with self.app.test_request_context():
            users_coll = self.app.db().users
            self.assertEqual(0, users_coll.count())

        self.mock_blenderid_validate_happy()
        token = 'this is my life now'
        self.get('/api/users/me', auth_token=token)

        with self.app.test_request_context():
            users_coll = self.app.db().users
            self.assertEqual(1, users_coll.count())

            db_user = users_coll.find()[0]
            self.assertEqual(db_user['email'], TEST_EMAIL_ADDRESS)

    def test_user_without_email_address(self):
        """Regular users should always have an email address.
        
        Regular users are created by authentication with Blender ID, so we do not
        have to test that (Blender ID ensures there is an email address). We do need
        to test PUT access to erase the email address, though.
        """

        from pillar.api.utils import remove_private_keys

        user_id = self.create_user(24 * 'd', token='user-token')

        with self.app.test_request_context():
            users_coll = self.app.db().users
            db_user = users_coll.find_one(user_id)

        puttable = remove_private_keys(db_user)

        empty_email = copy.deepcopy(puttable)
        empty_email['email'] = ''

        without_email = copy.deepcopy(puttable)
        del without_email['email']

        etag = db_user['_etag']
        resp = self.put(f'/api/users/{user_id}', json=puttable, etag=etag,
                        auth_token='user-token', expected_status=200).json()
        etag = resp['_etag']
        self.put(f'/api/users/{user_id}', json=empty_email, etag=etag,
                 auth_token='user-token', expected_status=422)
        self.put(f'/api/users/{user_id}', json=without_email, etag=etag,
                 auth_token='user-token', expected_status=422)

        # An admin should be able to edit this user, but also not clear the email address.
        self.create_user(24 * 'a', roles={'admin'}, token='admin-token')
        resp = self.put(f'/api/users/{user_id}', json=puttable, etag=etag,
                        auth_token='admin-token', expected_status=200).json()
        etag = resp['_etag']
        self.put(f'/api/users/{user_id}', json=empty_email, etag=etag,
                 auth_token='admin-token', expected_status=422)
        self.put(f'/api/users/{user_id}', json=without_email, etag=etag,
                 auth_token='admin-token', expected_status=422)
