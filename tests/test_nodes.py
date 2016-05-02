from bson import ObjectId
from eve.methods.post import post_internal
from eve.methods.put import put_internal
from flask import g
from werkzeug.exceptions import UnprocessableEntity

from common_test_class import AbstractPillarTest


class NodeContentTypeTest(AbstractPillarTest):
    def test_node_types(self):
        """Tests that the node's content_type properties is updated correctly from its file."""

        def mkfile(file_id, content_type):
            file_id, _ = self.ensure_file_exists(file_overrides={
                '_id': ObjectId(file_id),
                'content_type': content_type})
            return file_id

        file_id_image = mkfile('cafef00dcafef00dcafef00d', 'image/jpeg')
        file_id_video = mkfile('cafef00dcafef00dcafecafe', 'video/matroska')
        file_id_blend = mkfile('cafef00dcafef00ddeadbeef', 'application/x-blender')

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
