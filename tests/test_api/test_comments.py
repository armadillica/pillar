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

            comment_url = flask.url_for('nodes_api.patch_node_comment', node_path=str(self.node_id), comment_path=comment_id)
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
