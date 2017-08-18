import json

import pillar.tests.common_test_data as ctd
from bson import ObjectId
from flask import g
from mock import mock
from pillar.tests import AbstractPillarTest
from werkzeug.exceptions import UnprocessableEntity


class NodeContentTypeTest(AbstractPillarTest):
    def mkfile(self, file_id, content_type):
        file_id, _ = self.ensure_file_exists(file_overrides={
            '_id': ObjectId(file_id),
            'content_type': content_type})
        return file_id

    def test_node_types(self):
        """Tests that the node's content_type properties is updated correctly from its file."""

        file_id_image = self.mkfile('cafef00dcafef00dcafef00d', 'image/jpeg')
        file_id_video = self.mkfile('cafef00dcafef00dcafecafe', 'video/matroska')
        file_id_blend = self.mkfile('cafef00dcafef00ddeadbeef', 'application/x-blender')

        user_id = self.create_user()
        project_id, _ = self.ensure_project_exists()

        def perform_test(file_id, expected_type):
            node_doc = {'picture': file_id_image,
                        'description': '',
                        'project': project_id,
                        'node_type': 'asset',
                        'user': user_id,
                        'properties': {'status': 'published',
                                       'tags': [],
                                       'order': 0,
                                       'categories': ''},
                        'name': 'My first test node'}

            with self.app.test_request_context():
                self.login_api_as(user_id, roles={'subscriber', 'admin'},
                                  # This group is hardcoded in the EXAMPLE_PROJECT.
                                  group_ids=[ObjectId('5596e975ea893b269af85c0e')])
                nodes = self.app.data.driver.db['nodes']

                # Create the node.
                r, _, _, status = self.app.post_internal('nodes', node_doc)
                self.assertEqual(status, 201, r)
                node_id = r['_id']

                # Get from database to check its default content type.
                db_node = nodes.find_one(node_id)
                self.assertNotIn('content_type', db_node['properties'])

                # PUT it again, without a file -- should be blocked.
                self.assertRaises(UnprocessableEntity, self.app.put_internal, 'nodes', node_doc,
                                  _id=node_id)

                # PUT it with a file.
                node_doc['properties']['file'] = str(file_id)
                r, _, _, status = self.app.put_internal('nodes', node_doc, _id=node_id)
                self.assertEqual(status, 200, r)

                # Get from database to test the final node.
                db_node = nodes.find_one(node_id)
                self.assertEqual(expected_type, db_node['properties']['content_type'])

        perform_test(file_id_image, 'image')
        perform_test(file_id_video, 'video')
        perform_test(file_id_blend, 'file')

    def test_get_project_node_type(self):
        user_id = self.create_user()
        self.create_valid_auth_token(user_id, 'token')
        project_id, _ = self.ensure_project_exists()

        resp = self.client.get('/api/projects/%s?node_type=asset' % project_id)
        self.assertEqual(200, resp.status_code)

        data = json.loads(resp.data)
        self.assertEqual(['GET'], data['allowed_methods'])

    def test_default_picture_image_asset(self):
        from pillar.api.utils import dumps

        file_id_image = self.mkfile(24 * 'a', 'image/jpeg')
        file_id_video = self.mkfile(24 * 'b', 'video/matroska')
        file_id_image_spec = self.mkfile(24 * 'c', 'image/jpeg')
        file_id_image_bump = self.mkfile(24 * 'd', 'image/jpeg')

        user_id = self.create_user(groups=[ctd.EXAMPLE_ADMIN_GROUP_ID])
        self.create_valid_auth_token(user_id, 'token')
        project_id, _ = self.ensure_project_exists()

        def test_for(node, expected_picture_id):
            # Create the node
            resp = self.client.post('/api/nodes',
                                    data=dumps(node),
                                    headers={'Authorization': self.make_header('token'),
                                             'Content-Type': 'application/json'})
            self.assertEqual(resp.status_code, 201, resp.data)
            node_id = json.loads(resp.data)['_id']

            # Test that the node has the attached file as picture.
            resp = self.client.get('/api/nodes/%s' % node_id,
                                   headers={'Authorization': self.make_header('token')})
            self.assertEqual(resp.status_code, 200, resp.data)
            json_node = json.loads(resp.data)

            if expected_picture_id:
                self.assertEqual(ObjectId(json_node['picture']), expected_picture_id)
            else:
                self.assertNotIn('picture', json_node)

        # Image asset node
        test_for({'description': '',
                  'project': project_id,
                  'node_type': 'asset',
                  'user': user_id,
                  'properties': {'status': 'published',
                                 'tags': [],
                                 'order': 0,
                                 'categories': '',
                                 'file': file_id_image},
                  'name': 'Image asset'},
                 file_id_image)

        # Video asset node, should not get default picture
        test_for({'description': '',
                  'project': project_id,
                  'node_type': 'asset',
                  'user': user_id,
                  'properties': {'status': 'published',
                                 'tags': [],
                                 'order': 0,
                                 'categories': '',
                                 'file': file_id_video},
                  'name': 'Video asset'},
                 None)

        # Texture node, should default to colour map.
        test_for({'description': '',
                  'project': project_id,
                  'node_type': 'texture',
                  'user': user_id,
                  'properties': {'status': 'published',
                                 'tags': [],
                                 'order': 0,
                                 'categories': '',
                                 'files': [
                                     {'file': file_id_image_bump, 'map_type': 'bump'},
                                     {'file': file_id_image_spec, 'map_type': 'specular'},
                                     {'file': file_id_image, 'map_type': 'color'},
                                 ],
                                 'is_tileable': False,
                                 'aspect_ratio': 0.0,
                                 'is_landscape': False,
                                 'resolution': '',
                                 },
                  'name': 'Texture node'},
                 file_id_image)

        # Texture node, should default to first image if there is no colour map.
        test_for({'description': '',
                  'project': project_id,
                  'node_type': 'texture',
                  'user': user_id,
                  'properties': {'status': 'published',
                                 'tags': [],
                                 'order': 0,
                                 'categories': '',
                                 'files': [
                                     {'file': file_id_image_bump, 'map_type': 'bump'},
                                     {'file': file_id_image_spec, 'map_type': 'specular'},
                                 ],
                                 'is_tileable': False,
                                 'aspect_ratio': 0.0,
                                 'is_landscape': False,
                                 'resolution': '',
                                 },
                  'name': 'Texture node'},
                 file_id_image_bump)


class NodeOwnerTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        AbstractPillarTest.setUp(self, **kwargs)

        self.user_id = self.create_user()
        self.create_valid_auth_token(self.user_id, 'token')
        self.project_id, _ = self.ensure_project_exists(
            project_overrides={'permissions': {
                'users': [
                    {'user': self.user_id,
                     'methods': ['GET', 'PUT', 'POST', 'DELETE']}
                ]
            }}
        )

    def test_create_with_explicit_owner(self):
        test_node = {
            'project': self.project_id,
            'node_type': 'asset',
            'name': 'test with user',
            'user': self.user_id,
            'properties': {},
        }
        self._test_user(test_node)

    def test_create_with_implicit_owner(self):
        test_node = {
            'project': self.project_id,
            'node_type': 'asset',
            'name': 'test with user',
            'properties': {},
        }
        self._test_user(test_node)

    def _test_user(self, test_node):
        from pillar.api.utils import dumps

        resp = self.client.post('/api/nodes', data=dumps(test_node),
                                headers={'Authorization': self.make_header('token'),
                                         'Content-Type': 'application/json'})
        self.assertEqual(201, resp.status_code, resp.data)
        created = json.loads(resp.data)
        resp = self.client.get('/api/nodes/%s' % created['_id'],
                               headers={'Authorization': self.make_header('token')})
        self.assertEqual(200, resp.status_code, resp.data)
        json_node = json.loads(resp.data)
        self.assertEqual(str(self.user_id), json_node['user'])


class NodeSharingTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        AbstractPillarTest.setUp(self, **kwargs)

        self.project_id, _ = self.ensure_project_exists(
            project_overrides={
                'category': 'home',
                'permissions':
                    {'groups': [{'group': ctd.EXAMPLE_ADMIN_GROUP_ID,
                                  'methods': ['GET', 'POST', 'PUT', 'DELETE']}],
                     'users': [],
                     'world': []}}
        )
        self.user_id = self.create_user(groups=[ctd.EXAMPLE_ADMIN_GROUP_ID])
        self.create_valid_auth_token(self.user_id, 'token')

        # Create a node to share
        resp = self.post('/api/nodes', expected_status=201, auth_token='token', json={
            'project': self.project_id,
            'node_type': 'asset',
            'name': str(self),
            'properties': {},
        })
        self.node_id = resp.json()['_id']

    def _check_share_data(self, share_data):
        base_url = self.app.config['SHORT_LINK_BASE_URL']

        self.assertEqual(6, len(share_data['short_code']))
        self.assertTrue(share_data['short_link'].startswith(base_url))

    def test_share_node(self):
        # Share the node
        resp = self.post('/api/nodes/%s/share' % self.node_id, auth_token='token',
                         expected_status=201)
        share_data = resp.json()

        self._check_share_data(share_data)

    def test_anonymous_access_shared_node(self):
        # Anonymous user should not have access
        self.get('/api/nodes/%s' % self.node_id, expected_status=403)

        # Share the node
        self.post('/api/nodes/%s/share' % self.node_id, auth_token='token',
                  expected_status=201)

        # Check that an anonymous user has acces.
        resp = self.get('/api/nodes/%s' % self.node_id)
        self.assertEqual(str(self.node_id), resp.json()['_id'])

    def test_other_user_access_shared_node(self):
        # Share the node
        self.post('/api/nodes/%s/share' % self.node_id, auth_token='token',
                  expected_status=201)

        # Check that another user has access
        other_user_id = self.create_user(user_id=24 * 'a')
        self.create_valid_auth_token(other_user_id, 'other-token')
        resp = self.get('/api/nodes/%s' % self.node_id, auth_token='other-token')
        self.assertEqual(str(self.node_id), resp.json()['_id'])

    def test_get_share_data__unshared_node(self):
        self.get('/api/nodes/%s/share' % self.node_id,
                 expected_status=204,
                 auth_token='token')

    def test_get_share_data__shared_node(self):
        # Share the node first.
        self.post('/api/nodes/%s/share' % self.node_id, auth_token='token',
                  expected_status=201)

        # Then get its share info.
        resp = self.get('/api/nodes/%s/share' % self.node_id, auth_token='token')
        share_data = resp.json()

        self._check_share_data(share_data)

    def test_unauthenticated(self):
        self.post('/api/nodes/%s/share' % self.node_id,
                  expected_status=403)

    def test_other_user(self):
        other_user_id = self.create_user(user_id=24 * 'a')
        self.create_valid_auth_token(other_user_id, 'other-token')

        self.post('/api/nodes/%s/share' % self.node_id,
                  auth_token='other-token',
                  expected_status=403)

    def test_create_short_link(self):
        from pillar.api.nodes import create_short_code

        with self.app.test_request_context():
            length = self.app.config['SHORT_CODE_LENGTH']

            # We're testing a random process, so we have to repeat it
            # a few times to see if it really works.
            for _ in range(10000):
                short_code = create_short_code({})
                self.assertEqual(length, len(short_code))

    def test_short_code_collision(self):
        # Create a second node that has already been shared.
        self.post('/api/nodes', expected_status=201, auth_token='token', json={
            'project': self.project_id,
            'node_type': 'asset',
            'name': 'collider',
            'properties': {},
            'short_code': 'takenX',
        })

        # Mock create_short_code so that it returns predictable short codes.
        codes = ['takenX', 'takenX', 'freeXX']
        with mock.patch('pillar.api.nodes.create_short_code',
                        side_effect=codes) as create_short_link:
            resp = self.post('/api/nodes/%s/share' % self.node_id, auth_token='token',
                             expected_status=201)

        share_data = resp.json()

        self._check_share_data(share_data)
        self.assertEqual(3, create_short_link.call_count)

    def test_projections(self):
        """Projecting short_code should get us short_link as well."""

        # Share the node
        resp = self.post('/api/nodes/%s/share' % self.node_id, auth_token='token',
                         expected_status=201)
        share_data = resp.json()

        # Get the node with short_code
        resp = self.get('/api/nodes/%s' % self.node_id,
                        json={'projection': {'short_code': 1}})
        node = resp.json()
        self.assertEqual(node['short_code'], share_data['short_code'])
        self.assertTrue(node['short_link'].endswith(share_data['short_code']))

        # Get the node without short_code
        resp = self.get('/api/nodes/%s' % self.node_id,
                        qs={'projection': {'short_code': 0}})
        node = resp.json()
        self.assertNotIn('short_code', node)
        self.assertNotIn('short_link', node)
