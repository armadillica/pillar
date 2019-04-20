import json

from bson import ObjectId
import flask

from pillar.tests import AbstractPillarTest
from pillar.tests import common_test_data as ctd


class CommentTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        super().setUp(**kwargs)

        self.pid, self.project = self.ensure_project_exists()
        self.owner_uid = self.create_user(24 * 'a',
                                          groups=[ctd.EXAMPLE_ADMIN_GROUP_ID],
                                          token='admin-token')

        # Create a node people can comment on.
        self.node_id = self.create_node({
            '_id': ObjectId('572761099837730efe8e120d'),
            'description': 'This is an asset without file',
            'node_type': 'asset',
            'user': self.owner_uid,
            'properties': {
                'status': 'published',
                'content_type': 'image',
            },
            'name': 'Image test',
            'project': self.pid,
        })

        self.user_uid = self.create_user(24 * 'b', groups=[ctd.EXAMPLE_ADMIN_GROUP_ID],
                                         token='user-token')

    def test_write_comment(self):
        with self.login_as(self.user_uid):
            comment_url = flask.url_for('nodes_api.post_node_comment', node_path=str(self.node_id))
            self.post(
                comment_url,
                json={
                    'msg': 'je möder lives at [home](https://cloud.blender.org/)',
                },
                expected_status=201,
            )


class CommentEditTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        super().setUp(**kwargs)

        self.pid, self.project = self.ensure_project_exists()
        self.owner_uid = self.create_user(24 * 'a',
                                          groups=[ctd.EXAMPLE_ADMIN_GROUP_ID],
                                          token='admin-token')

        # Create a node people can comment on.
        self.node_id = self.create_node({
            '_id': ObjectId('572761099837730efe8e120d'),
            'description': 'This is an asset without file',
            'node_type': 'asset',
            'user': self.owner_uid,
            'properties': {
                'status': 'published',
                'content_type': 'image',
            },
            'name': 'Image test',
            'project': self.pid,
        })

        self.user_uid = self.create_user(24 * 'b', groups=[ctd.EXAMPLE_ADMIN_GROUP_ID],
                                         token='user-token')
        self.other_user_uid = self.create_user(24 * 'c',token='other-user-token')

        # Add world POST permission to comments for the project
        # This allows any user to post a comment
        for node_type in self.project['node_types']:
            if node_type['name'] != 'comment':
                continue
            node_type['permissions'] = {'world': ['POST']}

        with self.app.app_context():
            proj_coll = self.app.db('projects')
            proj_coll.update(
                {'_id': self.pid},
                {'$set': {
                    'node_types': self.project['node_types'],
                }})

    def test_edit_comment(self):
        # Create the comment
        with self.login_as(self.user_uid):
            comment_url = flask.url_for('nodes_api.post_node_comment', node_path=str(self.node_id))
            resp = self.post(
                comment_url,
                json={
                    'msg': 'je möder lives at [home](https://cloud.blender.org/)',
                },
                expected_status=201,
            )

            payload = json.loads(resp.data)
            comment_id = payload['id']

            comment_url = flask.url_for('nodes_api.patch_node_comment', node_path=str(self.node_id),
                                        comment_path=comment_id)
            # Edit the comment
            resp = self.patch(
                comment_url,
                json={
                    'msg': 'Edited comment',
                },
                expected_status=200,
            )

            self.assertEqual(200, resp.status_code)
            payload = json.loads(resp.data)
            self.assertEqual('Edited comment', payload['msg_markdown'])
            self.assertEqual('<p>Edited comment</p>\n', payload['msg_html'])

    def test_edit_comment_non_admin(self):
        """Verify that a comment can be edited by a regular user."""
        # Create the comment
        with self.login_as(self.other_user_uid):
            comment_url = flask.url_for('nodes_api.post_node_comment', node_path=str(self.node_id))
            resp = self.post(
                comment_url,
                json={
                    'msg': 'There is no place like [home](https://cloud.blender.org/)',
                },
                expected_status=201,
            )

            payload = json.loads(resp.data)

            # Check that the comment has edit (PUT) permission for the current user
            with self.app.app_context():
                nodes_coll = self.app.db('nodes')
                db_node = nodes_coll.find_one(ObjectId(payload['id']))
                expected_permissions = {'users': [{
                    'user': self.other_user_uid,
                    'methods': ['PUT']
                }]}
                self.assertEqual(db_node['permissions'], expected_permissions)

            comment_id = payload['id']
            comment_url = flask.url_for('nodes_api.patch_node_comment', node_path=str(self.node_id),
                                        comment_path=comment_id)
            # Edit the comment
            resp = self.patch(
                comment_url,
                json={
                    'msg': 'Edited comment',
                },
                expected_status=200,
            )

            self.assertEqual(200, resp.status_code)
            payload = json.loads(resp.data)
            self.assertEqual('Edited comment', payload['msg_markdown'])
            self.assertEqual('<p>Edited comment</p>\n', payload['msg_html'])
