# -*- encoding: utf-8 -*-

"""Unit tests for the user admin interface."""

from __future__ import absolute_import

import json
import logging

import responses
from bson import ObjectId
import flask_login
import pillarsdk
from pillar.tests import AbstractPillarTest, TEST_EMAIL_ADDRESS
from werkzeug import exceptions as wz_exceptions

log = logging.getLogger(__name__)


class UserAdminTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        AbstractPillarTest.setUp(self, **kwargs)
        self.create_standard_groups()

        from pillar.api.service import role_to_group_id
        self.subscriber_gid = role_to_group_id['subscriber']
        self.demo_gid = role_to_group_id['demo']

    def test_grant_subscriber_role(self):
        """There was a bug that group membership was lost when a user was edited."""

        import pillar.web.users.routes
        import pillar.auth

        user_id = self.create_user(roles=())
        self.create_valid_auth_token(user_id, 'token')

        # Try to access the home project, creating it.
        self.get('/api/bcloud/home-project',
                 auth_token='token')

        def get_dbuser():
            with self.app.test_request_context():
                db = self.app.db()
                return db['users'].find_one({'_id': user_id})

        db_user = get_dbuser()
        groups_pre_op = db_user['groups']
        self.assertEqual(1, len(groups_pre_op))
        home_project_gid = groups_pre_op[0]

        # Edit the user, granting subscriber and demo roles.
        admin_id = 24 * 'a'
        self.create_user(admin_id, roles=['admin'])
        self.create_valid_auth_token(admin_id, 'admin-token')

        def edit_user(roles):
            from pillar.web import system_util
            from pillar.web.users.forms import UserEditForm

            with self.app.test_request_context():
                api = system_util.pillar_api(token='admin-token')
                user = pillarsdk.User.find(user_id, api=api)

                form = UserEditForm()
                form.roles.data = roles
                pillar.web.users.routes._users_edit(form, user, api)

        edit_user(['subscriber', 'demo'])

        # Re-check the user group membership.
        groups = get_dbuser()['groups']
        self.assertEqual({home_project_gid, self.subscriber_gid, self.demo_gid},
                         set(groups))

        # Edit user again, revoking demo role.
        edit_user(['subscriber'])
        groups = get_dbuser()['groups']
        self.assertEqual({home_project_gid, self.subscriber_gid},
                         set(groups))
