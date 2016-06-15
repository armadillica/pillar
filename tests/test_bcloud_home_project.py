# -*- encoding: utf-8 -*-

"""Unit tests for the Blender Cloud home project module."""

import functools
import json
import logging
import urllib

import responses
from bson import ObjectId
from flask import g, url_for

from common_test_class import AbstractPillarTest, TEST_EMAIL_ADDRESS

log = logging.getLogger(__name__)


class HomeProjectTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        AbstractPillarTest.setUp(self, **kwargs)
        self.create_standard_groups()

    def _create_user_with_token(self, roles, token, user_id='cafef00df00df00df00df00d'):
        """Creates a user directly in MongoDB, so that it doesn't trigger any Eve hooks."""
        user_id = self.create_user(roles=roles, user_id=user_id)
        self.create_valid_auth_token(user_id, token)
        return user_id

    def test_create_home_project(self):
        from application.modules.blender_cloud import home_project
        from application.utils.authentication import validate_token

        user_id = self._create_user_with_token(roles={u'subscriber'}, token='token')

        # Test home project creation
        with self.app.test_request_context(headers={'Authorization': self.make_header('token')}):
            validate_token()

            proj = home_project.create_home_project(user_id)
            self.assertEqual('home', proj['category'])
            self.assertEqual({u'text', u'group', u'asset'},
                             set(nt['name'] for nt in proj['node_types']))

            endpoint = url_for('blender_cloud.home_project.home_project')
            db_proj = self.app.data.driver.db['projects'].find_one(proj['_id'])

        # Test availability at end-point
        resp = self.client.get(endpoint)
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

        # Grant subscriber role, and fetch the home project.
        self.badger(TEST_EMAIL_ADDRESS, 'subscriber', 'grant')

        resp = self.client.get('/bcloud/home-project',
                               headers={'Authorization': self.make_header('token')})
        self.assertEqual(200, resp.status_code)

        json_proj = json.loads(resp.data)
        self.assertEqual('home', json_proj['category'])

    @responses.activate
    def test_autocreate_home_project_with_demo_role(self):
        # Implicitly create user by token validation.
        self.mock_blenderid_validate_happy()
        resp = self.client.get('/users/me', headers={'Authorization': self.make_header('token')})
        self.assertEqual(200, resp.status_code, resp)

        # Grant demo role, which should allow creation of the home project.
        self.badger(TEST_EMAIL_ADDRESS, 'demo', 'grant')

        resp = self.client.get('/bcloud/home-project',
                               headers={'Authorization': self.make_header('token')})
        self.assertEqual(200, resp.status_code)

        json_proj = json.loads(resp.data)
        self.assertEqual('home', json_proj['category'])

    @responses.activate
    def test_autocreate_home_project_with_succubus_role(self):
        # Implicitly create user by token validation.
        self.mock_blenderid_validate_happy()
        resp = self.client.get('/users/me', headers={'Authorization': self.make_header('token')})
        self.assertEqual(200, resp.status_code, resp)

        # Grant demo role, which should NOT allow creation fo the home project.
        self.badger(TEST_EMAIL_ADDRESS, 'succubus', 'grant')

        resp = self.client.get('/bcloud/home-project',
                               headers={'Authorization': self.make_header('token')})
        self.assertEqual(403, resp.status_code)

    def test_has_home_project(self):
        from application.modules.blender_cloud import home_project
        from application.utils.authentication import validate_token

        user_id = self._create_user_with_token(roles={u'subscriber'}, token='token')

        # Test home project creation
        with self.app.test_request_context(headers={'Authorization': self.make_header('token')}):
            validate_token()

            self.assertFalse(home_project.has_home_project(user_id))
            proj = home_project.create_home_project(user_id)
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
        self.badger(TEST_EMAIL_ADDRESS, 'subscriber', 'grant')

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
        self.badger(TEST_EMAIL_ADDRESS, 'subscriber', 'grant')

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
            proj1 = home_project.create_home_project(uid1)
            db_proj1 = self.app.data.driver.db['projects'].find_one(proj1['_id'])

        with self.app.test_request_context(headers={'Authorization': self.make_header('token2')}):
            validate_token()
            proj2 = home_project.create_home_project(uid2)
            db_proj2 = self.app.data.driver.db['projects'].find_one(proj2['_id'])

        # Test availability at end-point
        resp1 = self.client.get('/bcloud/home-project', headers={'Authorization': self.make_header('token1')})
        resp2 = self.client.get('/bcloud/home-project', headers={'Authorization': self.make_header('token2')})
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
