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
            comment_url = flask.url_for('nodes.comments_create')
            self.post(
                comment_url,
                data={
                    'content': 'je möder lives at [home](https://cloud.blender.org/)',
                    'parent_id': str(self.node_id),
                },
                expected_status=201,
            )


class CommentEditTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        super().setUp(**kwargs)

        self.pid, self.project = self.ensure_project_exists()
        self.uid = self.create_user(groups=[ctd.EXAMPLE_ADMIN_GROUP_ID])
        self.create_valid_auth_token(self.uid, 'token')

        self.node_id = self.create_node({
            '_id': ObjectId('572761099837730efe8e120d'),
            'description': 'This is an asset without file',
            'node_type': 'asset',
            'user': self.uid,
            'properties': {
                'status': 'published',
                'content_type': 'image',
            },
            'name': 'Image test',
            'project': self.pid,
        })

    def test_edit_comment(self):
        from pillar import auth
        from pillar.web.nodes.custom import comments

        # Create the comment
        with self.app.test_request_context(method='POST', data={
            'content': 'My first comment',
            'parent_id': str(self.node_id),
        }):
            auth.login_user('token', load_from_db=True)
            resp, status = comments.comments_create()

        self.assertEqual(201, status)
        payload = json.loads(resp.data)
        comment_id = payload['node_id']

        # Edit the comment
        with self.app.test_request_context(method='POST', data={
            'content': 'Edited comment',
        }):
            auth.login_user('token', load_from_db=True)
            resp = comments.comment_edit(comment_id)

        self.assertEqual(200, resp.status_code)
        payload = json.loads(resp.data)
        self.assertEqual('success', payload['status'])
        self.assertEqual('Edited comment', payload['data']['content'])
        self.assertEqual('<p>Edited comment</p>\n', payload['data']['content_html'])
