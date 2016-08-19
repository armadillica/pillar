"""Test badger service."""

from pillar.tests import AbstractPillarTest, TEST_EMAIL_ADDRESS


class BadgerServiceTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        AbstractPillarTest.setUp(self, **kwargs)

        from pillar.api import service

        with self.app.test_request_context():
            self.badger, token_doc = service.create_service_account(
                'serviceaccount@example.com', [u'badger'],
                {u'badger': [u'succubus', u'subscriber', u'demo']}
            )
            self.badger_token = token_doc['token']

            self.user_id = self.create_user()
            self.user_email = TEST_EMAIL_ADDRESS

    def _post(self, data):
        from pillar.api.utils import dumps
        return self.client.post('/api/service/badger',
                                data=dumps(data),
                                headers={'Authorization': self.make_header(self.badger_token),
                                         'Content-Type': 'application/json'})

    def test_grant_revoke_badge(self):
        # Grant the badge
        resp = self._post({'action': 'grant', 'user_email': self.user_email, 'role': 'succubus'})
        self.assertEqual(204, resp.status_code)

        with self.app.test_request_context():
            user = self.app.data.driver.db['users'].find_one(self.user_id)
            self.assertIn(u'succubus', user['roles'])

        # Aaaahhhw it's gone again
        resp = self._post({'action': 'revoke', 'user_email': self.user_email, 'role': 'succubus'})
        self.assertEqual(204, resp.status_code)

        with self.app.test_request_context():
            user = self.app.data.driver.db['users'].find_one(self.user_id)
            self.assertNotIn(u'succubus', user['roles'])

    def test_grant_not_allowed_badge(self):
        resp = self._post({'action': 'grant', 'user_email': self.user_email, 'role': 'admin'})
        self.assertEqual(403, resp.status_code)

        with self.app.test_request_context():
            user = self.app.data.driver.db['users'].find_one(self.user_id)
            self.assertNotIn(u'admin', user['roles'])

    def test_group_membership(self):
        """Certain roles are linked to certain groups."""

        group_ids = self.create_standard_groups(additional_groups=['succubus'])

        with self.app.test_request_context():
            def test_for_group(group_name, test=self.assertIn):
                # Assign the 'subscriber' role
                resp = self._post({'action': 'grant',
                                   'user_email': self.user_email,
                                   'role': group_name})
                self.assertEqual(204, resp.status_code)

                # Check that the user is actually member of that group.
                user = self.app.data.driver.db['users'].find_one(self.user_id)
                test(group_ids[group_name], user['groups'])

            # There are special groups for those. Also for admin, but if
            # it works for those, it also works for admin, and another test
            # case requires admin to be ingrantable.
            test_for_group('demo')
            test_for_group('subscriber')

            # This role isn't linked to group membership.
            test_for_group('succubus', test=self.assertNotIn)

    def test_project_groups(self):
        """Projects groups should be maintained."""

        group_ids = self.create_standard_groups()

        with self.app.test_request_context():
            user_coll = self.app.data.driver.db['users']

            def test_group_membership(expected_groups):
                user = user_coll.find_one(self.user_id)
                self.assertEqual(expected_groups, set(user['groups']))

            # Fresh user, no roles.
            test_group_membership(set())

            # Add some groups
            user_coll.update_one({'_id': self.user_id},
                                 {'$set': {'groups': ['project1', 'project2']}})
            test_group_membership({'project1', 'project2'})

            # Grant subscriber role.
            resp = self._post({'action': 'grant',
                               'user_email': self.user_email,
                               'role': 'subscriber'})
            self.assertEqual(204, resp.status_code)
            test_group_membership({'project1', 'project2', group_ids['subscriber']})
