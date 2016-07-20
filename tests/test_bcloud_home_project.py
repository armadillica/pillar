# -*- encoding: utf-8 -*-

"""Unit tests for the Blender Cloud home project module."""

import json
import logging

import responses
from bson import ObjectId
from flask import url_for
from werkzeug import exceptions as wz_exceptions

from common_test_class import AbstractPillarTest, TEST_EMAIL_ADDRESS

log = logging.getLogger(__name__)


class AbstractHomeProjectTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        AbstractPillarTest.setUp(self, **kwargs)
        self.create_standard_groups()

    def _create_user_with_token(self, roles, token, user_id='cafef00df00df00df00df00d'):
        """Creates a user directly in MongoDB, so that it doesn't trigger any Eve hooks.

        Adds the 'homeproject' role too, which we need to get past the AB-testing.
        """
        user_id = self.create_user(roles=roles.union({u'homeproject'}), user_id=user_id)
        self.create_valid_auth_token(user_id, token)
        return user_id


class HomeProjectTest(AbstractHomeProjectTest):
    def test_create_home_project(self):
        from application.modules.blender_cloud import home_project
        from application.utils.authentication import validate_token

        user_id = self._create_user_with_token(roles={u'subscriber'}, token='token')

        # Test home project creation
        with self.app.test_request_context(headers={'Authorization': self.make_header('token')}):
            validate_token()

            proj = home_project.create_home_project(user_id, write_access=True)
            self.assertEqual('home', proj['category'])
            self.assertEqual({u'group', u'asset', u'comment'},
                             set(nt['name'] for nt in proj['node_types']))

            endpoint = url_for('blender_cloud.home_project.home_project')
            db_proj = self.app.data.driver.db['projects'].find_one(proj['_id'])

        # Test availability at end-point
        resp = self.client.get(endpoint)
        # While we're still AB-testing, unauthenticated users should get a 404.
        # When that's over, it should result in a 403.
        self.assertEqual(403, resp.status_code)

        resp = self.client.get(endpoint, headers={'Authorization': self.make_header('token')})
        self.assertEqual(200, resp.status_code)

        json_proj = json.loads(resp.data)
        self.assertEqual(ObjectId(json_proj['_id']), proj['_id'])
        self.assertEqual(json_proj['_etag'], db_proj['_etag'])

    @responses.activate
    def test_autocreate_home_project_with_subscriber_role(self):
        # Implicitly create user by token validation.
        self.mock_blenderid_validate_happy()
        resp = self.client.get('/users/me', headers={'Authorization': self.make_header('token')})
        self.assertEqual(200, resp.status_code, resp)

        # Grant subscriber and homeproject roles, and fetch the home project.
        self.badger(TEST_EMAIL_ADDRESS, {'subscriber', 'homeproject'}, 'grant')

        resp = self.client.get('/bcloud/home-project',
                               headers={'Authorization': self.make_header('token')})
        self.assertEqual(200, resp.status_code)

        json_proj = json.loads(resp.data)
        self.assertEqual('home', json_proj['category'])
        self.assertEqual('home', json_proj['url'])

        # Check that a Blender Sync node was created automatically.
        with self.app.test_request_context(headers={'Authorization': self.make_header('token')}):
            nodes_coll = self.app.data.driver.db['nodes']
            node = nodes_coll.find_one({
                'project': ObjectId(json_proj['_id']),
                'node_type': 'group',
                'name': 'Blender Sync',
            })
            self.assertIsNotNone(node)

    # @responses.activate
    # def test_home_project_ab_testing(self):
    #     self.mock_blenderid_validate_happy()
    #     resp = self.client.get('/users/me', headers={'Authorization': self.make_header('token')})
    #     self.assertEqual(200, resp.status_code, resp)
    #
    #     # Grant subscriber and but NOT homeproject role, and fetch the home project.
    #     self.badger(TEST_EMAIL_ADDRESS, {'subscriber'}, 'grant')
    #
    #     resp = self.client.get('/bcloud/home-project',
    #                            headers={'Authorization': self.make_header('token')})
    #     self.assertEqual(404, resp.status_code)
    #
    #     resp = self.client.get('/users/me',
    #                            headers={'Authorization': self.make_header('token')})
    #     self.assertEqual(200, resp.status_code)
    #     me = json.loads(resp.data)
    #
    #     with self.app.test_request_context():
    #         from application.modules.blender_cloud import home_project
    #         self.assertFalse(home_project.has_home_project(me['_id']))

    @responses.activate
    def test_autocreate_home_project_with_demo_role(self):
        # Implicitly create user by token validation.
        self.mock_blenderid_validate_happy()
        resp = self.client.get('/users/me', headers={'Authorization': self.make_header('token')})
        self.assertEqual(200, resp.status_code, resp)

        # Grant demo and homeproject role, which should allow creation of the home project.
        self.badger(TEST_EMAIL_ADDRESS, {'demo', 'homeproject'}, 'grant')

        resp = self.client.get('/bcloud/home-project',
                               headers={'Authorization': self.make_header('token')})
        self.assertEqual(200, resp.status_code)

        json_proj = json.loads(resp.data)
        self.assertEqual('home', json_proj['category'])
        self.assertEqual('home', json_proj['url'])

        # Check that a Blender Sync node was created automatically.
        with self.app.test_request_context(headers={'Authorization': self.make_header('token')}):
            nodes_coll = self.app.data.driver.db['nodes']
            node = nodes_coll.find_one({
                'project': ObjectId(json_proj['_id']),
                'node_type': 'group',
                'name': 'Blender Sync',
            })
            self.assertIsNotNone(node)

    @responses.activate
    def test_autocreate_home_project_with_succubus_role(self):
        from application.utils import dumps

        # Implicitly create user by token validation.
        self.mock_blenderid_validate_happy()
        resp = self.client.get('/users/me', headers={'Authorization': self.make_header('token')})
        self.assertEqual(200, resp.status_code, resp.data)
        user_id = ObjectId(json.loads(resp.data)['_id'])

        # Grant succubus role, which should allow creation of a read-only home project.
        self.badger(TEST_EMAIL_ADDRESS, {'succubus', 'homeproject'}, 'grant')

        resp = self.client.get('/bcloud/home-project',
                               headers={'Authorization': self.make_header('token')})
        self.assertEqual(200, resp.status_code)
        json_proj = json.loads(resp.data)
        self.assertEqual('home', json_proj['category'])
        self.assertEqual('home', json_proj['url'])

        # Check that the admin group of the project only has GET permissions.
        self.assertEqual({'GET'}, set(json_proj['permissions']['groups'][0]['methods']))
        project_id = ObjectId(json_proj['_id'])
        admin_group_id = json_proj['permissions']['groups'][0]['group']

        # Check that a Blender Sync node was created automatically.
        expected_node_permissions = {u'users': [],
                                     u'groups': [
                                         {u'group': ObjectId(admin_group_id),
                                          u'methods': [u'GET', u'PUT', u'POST', u'DELETE']}, ],
                                     u'world': []}
        with self.app.test_request_context(headers={'Authorization': self.make_header('token')}):
            nodes_coll = self.app.data.driver.db['nodes']
            node = nodes_coll.find_one({
                'project': project_id,
                'node_type': 'group',
                'name': 'Blender Sync',
            })
            self.assertIsNotNone(node)

            # Check that the node itself has write permissions for the admin group.
            node_perms = node['permissions']
            self.assertEqual(node_perms, expected_node_permissions)
            sync_node_id = node['_id']

        # Check that we can create a group node inside the sync node.
        sub_sync_node = {'project': project_id,
                         'node_type': 'group',
                         'parent': sync_node_id,
                         'name': '2.77',
                         'user': user_id,
                         'description': 'Sync folder for Blender 2.77',
                         'properties': {'status': 'published'},
                         }
        resp = self.client.post('/nodes', data=dumps(sub_sync_node),
                                headers={'Authorization': self.make_header('token'),
                                         'Content-Type': 'application/json'}
                                )
        self.assertEqual(201, resp.status_code, resp.data)
        sub_node_info = json.loads(resp.data)

        # Check the explicit node-level permissions are copied.
        # These aren't returned by the POST to Eve, so we have to check them in the DB manually.
        with self.app.test_request_context(headers={'Authorization': self.make_header('token')}):
            nodes_coll = self.app.data.driver.db['nodes']
            sub_node = nodes_coll.find_one(ObjectId(sub_node_info['_id']))

            node_perms = sub_node['permissions']
            self.assertEqual(node_perms, expected_node_permissions)

    def test_has_home_project(self):
        from application.modules.blender_cloud import home_project
        from application.utils.authentication import validate_token

        user_id = self._create_user_with_token(roles={u'subscriber'}, token='token')

        # Test home project creation
        with self.app.test_request_context(headers={'Authorization': self.make_header('token')}):
            validate_token()

            self.assertFalse(home_project.has_home_project(user_id))
            proj = home_project.create_home_project(user_id, write_access=True)
            self.assertTrue(home_project.has_home_project(user_id))

            # Delete the project.
            resp = self.client.delete('/projects/%s' % proj['_id'],
                                      headers={'Authorization': self.make_header('token'),
                                               'If-Match': proj['_etag']})
            self.assertEqual(204, resp.status_code, resp.data)
            self.assertFalse(home_project.has_home_project(user_id))

    @responses.activate
    def test_home_project_projections(self):
        """Getting the home project should support projections."""

        # Implicitly create user by token validation.
        self.mock_blenderid_validate_happy()
        resp = self.client.get('/users/me', headers={'Authorization': self.make_header('token')})
        self.assertEqual(200, resp.status_code, resp)

        # Grant subscriber role, and fetch the home project.
        self.badger(TEST_EMAIL_ADDRESS, {'subscriber', 'homeproject'}, 'grant')

        resp = self.client.get('/bcloud/home-project',
                               query_string={'projection': json.dumps(
                                   {'permissions': 1,
                                    'category': 1,
                                    'user': 1})},
                               headers={'Authorization': self.make_header('token')})
        self.assertEqual(200, resp.status_code, resp.data)

        json_proj = json.loads(resp.data)
        self.assertNotIn('name', json_proj)
        self.assertNotIn('node_types', json_proj)
        self.assertEqual('home', json_proj['category'])

    @responses.activate
    def test_home_project_url(self):
        """The home project should have 'home' as URL."""

        # Implicitly create user by token validation.
        self.mock_blenderid_validate_happy()
        resp = self.client.get('/users/me', headers={'Authorization': self.make_header('token')})
        self.assertEqual(200, resp.status_code, resp)

        # Grant subscriber role, and fetch the home project.
        self.badger(TEST_EMAIL_ADDRESS, {'subscriber', 'homeproject'}, 'grant')

        resp = self.client.get('/bcloud/home-project',
                               headers={'Authorization': self.make_header('token')})
        self.assertEqual(200, resp.status_code, resp.data)

        json_proj = json.loads(resp.data)
        self.assertEqual('home', json_proj['url'])

    @responses.activate
    def test_multiple_users_with_home_project(self):
        from application.modules.blender_cloud import home_project
        from application.utils.authentication import validate_token

        uid1 = self._create_user_with_token(roles={u'subscriber'}, token='token1', user_id=24 * 'a')
        uid2 = self._create_user_with_token(roles={u'subscriber'}, token='token2', user_id=24 * 'b')

        # Create home projects
        with self.app.test_request_context(headers={'Authorization': self.make_header('token1')}):
            validate_token()
            proj1 = home_project.create_home_project(uid1, write_access=True)
            db_proj1 = self.app.data.driver.db['projects'].find_one(proj1['_id'])

        with self.app.test_request_context(headers={'Authorization': self.make_header('token2')}):
            validate_token()
            proj2 = home_project.create_home_project(uid2, write_access=True)
            db_proj2 = self.app.data.driver.db['projects'].find_one(proj2['_id'])

        # Test availability at end-point
        resp1 = self.client.get('/bcloud/home-project',
                                headers={'Authorization': self.make_header('token1')})
        resp2 = self.client.get('/bcloud/home-project',
                                headers={'Authorization': self.make_header('token2')})
        self.assertEqual(200, resp1.status_code)
        self.assertEqual(200, resp2.status_code)

        json_proj1 = json.loads(resp1.data)
        json_proj2 = json.loads(resp2.data)

        self.assertEqual(ObjectId(json_proj1['_id']), proj1['_id'])
        self.assertEqual(ObjectId(json_proj2['_id']), proj2['_id'])
        self.assertEqual(json_proj1['_etag'], db_proj1['_etag'])
        self.assertEqual(json_proj2['_etag'], db_proj2['_etag'])
        self.assertNotEqual(db_proj1['_etag'], db_proj2['_etag'])
        self.assertNotEqual(db_proj1['_id'], db_proj2['_id'])

    def test_delete_restore(self):
        """Deleting and then recreating a home project should restore the deleted project."""

        self._create_user_with_token(roles={u'subscriber'}, token='token')

        # Create home project by getting it.
        resp = self.client.get('/bcloud/home-project',
                               headers={'Authorization': self.make_header('token')})
        self.assertEqual(200, resp.status_code, resp.data)
        before_delete_json_proj = json.loads(resp.data)

        # Delete the project.
        resp = self.client.delete('/projects/%s' % before_delete_json_proj['_id'],
                                  headers={'Authorization': self.make_header('token'),
                                           'If-Match': before_delete_json_proj['_etag']})
        self.assertEqual(204, resp.status_code, resp.data)

        # Recreate home project by getting it.
        resp = self.client.get('/bcloud/home-project',
                               headers={'Authorization': self.make_header('token')})
        self.assertEqual(200, resp.status_code, resp.data)
        after_delete_json_proj = json.loads(resp.data)

        self.assertEqual(before_delete_json_proj['_id'],
                         after_delete_json_proj['_id'])


class HomeProjectUserChangedRoleTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        AbstractPillarTest.setUp(self, **kwargs)
        self.create_standard_groups()

    def test_without_home_project(self):
        from application.modules.blender_cloud import home_project

        self.user_id = self.create_user()

        with self.app.test_request_context():
            changed = home_project.user_changed_role(None, {'_id': self.user_id})
            self.assertFalse(changed)

            # Shouldn't do anything, shouldn't crash either.

    def test_already_subscriber_role(self):
        from application.modules.blender_cloud import home_project
        from application.utils.authentication import validate_token

        self.user_id = self.create_user(roles=set('subscriber'))
        self.create_valid_auth_token(self.user_id, 'token')

        with self.app.test_request_context(headers={'Authorization': self.make_header('token')}):
            validate_token()

            home_proj = home_project.create_home_project(self.user_id, write_access=True)
            changed = home_project.user_changed_role(None, {'_id': self.user_id,
                                                            'roles': ['subscriber']})
            self.assertFalse(changed)

        # The home project should still be writable, so we should be able to create a node.
        self.create_test_node(home_proj['_id'])

    def test_granting_subscriber_role(self):
        from application.modules.blender_cloud import home_project
        from application.utils.authentication import validate_token

        self.user_id = self.create_user(roles=set())
        self.create_valid_auth_token(self.user_id, 'token')

        with self.app.test_request_context(headers={'Authorization': self.make_header('token')}):
            validate_token()

            home_proj = home_project.create_home_project(self.user_id, write_access=False)
            changed = home_project.user_changed_role(None, {'_id': self.user_id,
                                                            'roles': ['subscriber']})
            self.assertTrue(changed)

        # The home project should be writable, so we should be able to create a node.
        self.create_test_node(home_proj['_id'])

    def test_revoking_subscriber_role(self):
        from application.modules.blender_cloud import home_project
        from application.utils.authentication import validate_token

        self.user_id = self.create_user(roles=set('subscriber'))
        self.create_valid_auth_token(self.user_id, 'token')

        with self.app.test_request_context(headers={'Authorization': self.make_header('token')}):
            validate_token()

            home_proj = home_project.create_home_project(self.user_id, write_access=True)
            changed = home_project.user_changed_role(None, {'_id': self.user_id,
                                                            'roles': []})
            self.assertTrue(changed)

        # The home project should NOT be writable, so we should NOT be able to create a node.
        self.create_test_node(home_proj['_id'], 403)

    def create_test_node(self, project_id, status_code=201):
        from application.utils import dumps

        node = {
            'project': project_id,
            'node_type': 'group',
            'name': 'test group node',
            'user': self.user_id,
            'properties': {},
        }

        resp = self.client.post('/nodes', data=dumps(node),
                                headers={'Authorization': self.make_header('token'),
                                         'Content-Type': 'application/json'})
        self.assertEqual(status_code, resp.status_code, resp.data)


class TextureLibraryTest(AbstractHomeProjectTest):
    def create_node(self, node_doc):
        with self.app.test_request_context():
            nodes_coll = self.app.data.driver.db['nodes']
            result = nodes_coll.insert_one(node_doc)
        return result.inserted_id

    def setUp(self, **kwargs):
        AbstractHomeProjectTest.setUp(self, **kwargs)

        user_id = self._create_user_with_token(set(), 'token')
        self.hdri_proj_id, proj = self.ensure_project_exists(project_overrides={'_id': 24 * 'a'})
        self.tex_proj_id, proj2 = self.ensure_project_exists(project_overrides={'_id': 24 * 'b'})

        self.create_node({'description': '',
                          'project': self.hdri_proj_id,
                          'node_type': 'group_hdri',
                          'user': user_id,
                          'properties': {'status': 'published',
                                         'tags': [],
                                         'order': 0,
                                         'categories': '',
                                         'files': ''},
                          'name': 'HDRi test node'}
                         )

        self.create_node({'description': '',
                          'project': self.tex_proj_id,
                          'node_type': 'group_texture',
                          'user': user_id,
                          'properties': {'status': 'published',
                                         'tags': [],
                                         'order': 0,
                                         'categories': '',
                                         'files': ''},
                          'name': 'Group texture test node'}
                         )

    def test_blender_cloud_addon_version(self):
        from application.modules.blender_cloud import blender_cloud_addon_version

        # Three-digit version
        with self.app.test_request_context(headers={'Blender-Cloud-Addon': '1.3.3'}):
            self.assertEqual((1, 3, 3), blender_cloud_addon_version())

        # Two-digit version
        with self.app.test_request_context(headers={'Blender-Cloud-Addon': '1.5'}):
            self.assertEqual((1, 5), blender_cloud_addon_version())

        # No version
        with self.app.test_request_context():
            self.assertEqual(None, blender_cloud_addon_version())

        # Malformed version
        with self.app.test_request_context(headers={'Blender-Cloud-Addon': 'je moeder'}):
            self.assertRaises(wz_exceptions.BadRequest, blender_cloud_addon_version)

    def test_hdri_library__no_bcloud_version(self):
        resp = self.get('/bcloud/texture-libraries', auth_token='token')
        libs = resp.json()['_items']
        library_project_ids = {proj['_id'] for proj in libs}

        self.assertNotIn(unicode(self.hdri_proj_id), library_project_ids)
        self.assertIn(unicode(self.tex_proj_id), library_project_ids)

    def test_hdri_library__old_bcloud_addon(self):
        resp = self.get('/bcloud/texture-libraries',
                        auth_token='token',
                        headers={'Blender-Cloud-Addon': '1.3.3'})
        libs = resp.json()['_items']
        library_project_ids = {proj['_id'] for proj in libs}
        self.assertNotIn(unicode(self.hdri_proj_id), library_project_ids)
        self.assertIn(unicode(self.tex_proj_id), library_project_ids)

    def test_hdri_library__new_bcloud_addon(self):
        resp = self.get('/bcloud/texture-libraries',
                        auth_token='token',
                        headers={'Blender-Cloud-Addon': '1.4.0'})
        libs = resp.json()['_items']
        library_project_ids = {proj['_id'] for proj in libs}
        self.assertIn(unicode(self.hdri_proj_id), library_project_ids)
        self.assertIn(unicode(self.tex_proj_id), library_project_ids)
