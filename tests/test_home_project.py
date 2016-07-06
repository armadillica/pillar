# -*- encoding: utf-8 -*-

from common_test_class import AbstractPillarTest


class HomeProjectUserChangedRoleTest(AbstractPillarTest):
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
