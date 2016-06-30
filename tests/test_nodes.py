import json

from bson import ObjectId
from eve.methods.post import post_internal
from eve.methods.put import put_internal
from flask import g
from werkzeug.exceptions import UnprocessableEntity

from common_test_class import AbstractPillarTest
import common_test_data as ctd


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
                g.current_user = {'user_id': user_id,
                                  # This group is hardcoded in the EXAMPLE_PROJECT.
                                  'groups': [ObjectId('5596e975ea893b269af85c0e')],
                                  'roles': {u'subscriber', u'admin'}}
                nodes = self.app.data.driver.db['nodes']

                # Create the node.
                r, _, _, status = post_internal('nodes', node_doc)
                self.assertEqual(status, 201, r)
                node_id = r['_id']

                # Get from database to check its default content type.
                db_node = nodes.find_one(node_id)
                self.assertNotIn('content_type', db_node['properties'])

                # PUT it again, without a file -- should be blocked.
                self.assertRaises(UnprocessableEntity, put_internal, 'nodes', node_doc,
                                  _id=node_id)

                # PUT it with a file.
                node_doc['properties']['file'] = str(file_id)
                r, _, _, status = put_internal('nodes', node_doc, _id=node_id)
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

        resp = self.client.get('/projects/%s?node_type=asset' % project_id)
        self.assertEqual(200, resp.status_code)

        data = json.loads(resp.data)
        self.assertEqual([u'GET'], data['allowed_methods'])

    def test_default_picture_image_asset(self):
        from application.utils import dumps

        file_id_image = self.mkfile(24 * 'a', 'image/jpeg')
        file_id_video = self.mkfile(24 * 'b', 'video/matroska')
        file_id_image_spec = self.mkfile(24 * 'c', 'image/jpeg')
        file_id_image_bump = self.mkfile(24 * 'd', 'image/jpeg')

        user_id = self.create_user(groups=[ctd.EXAMPLE_ADMIN_GROUP_ID])
        self.create_valid_auth_token(user_id, 'token')
        project_id, _ = self.ensure_project_exists()

        def test_for(node, expected_picture_id):
            # Create the node
            resp = self.client.post('/nodes',
                                    data=dumps(node),
                                    headers={'Authorization': self.make_header('token'),
                                             'Content-Type': 'application/json'})
            self.assertEqual(resp.status_code, 201, resp.data)
            node_id = json.loads(resp.data)['_id']

            # Test that the node has the attached file as picture.
            resp = self.client.get('/nodes/%s' % node_id,
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
