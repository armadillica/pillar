import bson

from pillar.tests import AbstractPillarTest


class UsersTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        super().setUp(**kwargs)

        self.group_names = [f'test{num}' for num in range(10)]
        self.group_map = self.create_standard_groups(additional_groups=self.group_names)

    def test_add_user_to_group_happy(self):
        from pillar.api import users

        user_id = bson.ObjectId(24 * '1')

        self.create_user(user_id, roles={'subscriber'}, groups=[self.group_map['subscriber']])

        db_user = self.fetch_user_from_db(user_id)
        self.assertEqual([self.group_map['subscriber']], db_user['groups'])

        with self.app.test_request_context():
            users.add_user_to_group(user_id, self.group_map['test1'])

        db_user = self.fetch_user_from_db(user_id)
        self.assertEqual([
            self.group_map['subscriber'],
            self.group_map['test1'],
        ], db_user['groups'])

    def test_add_user_to_group_no_initial_groups(self):
        from pillar.api import users

        user_id = bson.ObjectId(24 * '1')
        self.create_user(user_id, roles=set())

        with self.app.test_request_context():
            # Ensure the user doesn't even have a 'groups' property.
            users_coll = self.app.db('users')
            users_coll.update_one({'_id': user_id}, {'$unset': {'groups': 1}})
            db_user = self.fetch_user_from_db(user_id)
            self.assertNotIn('groups', db_user)

            users.add_user_to_group(user_id, self.group_map['test1'])

        db_user = self.fetch_user_from_db(user_id)
        self.assertEqual([
            self.group_map['test1'],
        ], db_user['groups'])

    def test_remove_user_from_group_happy(self):
        from pillar.api import users

        user_id = bson.ObjectId(24 * '1')

        self.create_user(user_id, roles={'subscriber'}, groups=[
            self.group_map['subscriber'],
            self.group_map['test1'],
        ])

        # Remove from existing group
        with self.app.test_request_context():
            users.remove_user_from_group(user_id, self.group_map['test1'])

        db_user = self.fetch_user_from_db(user_id)
        self.assertEqual([self.group_map['subscriber']], db_user['groups'])

        # Remove same group again, should be no-op
        with self.app.test_request_context():
            users.remove_user_from_group(user_id, self.group_map['test1'])

        db_user = self.fetch_user_from_db(user_id)
        self.assertEqual([self.group_map['subscriber']], db_user['groups'])

        # Remove from last group, should result in empty list.
        with self.app.test_request_context():
            users.remove_user_from_group(user_id, self.group_map['subscriber'])

        db_user = self.fetch_user_from_db(user_id)
        self.assertEqual([], db_user['groups'])

        # Remove non-existing group from empty list, should also work.
        with self.app.test_request_context():
            users.remove_user_from_group(user_id, bson.ObjectId())

        db_user = self.fetch_user_from_db(user_id)
        self.assertEqual([], db_user['groups'])

    def test_replace_user_without_roles(self):
        from pillar.api.utils import remove_private_keys

        self.enter_app_context()

        user_id = bson.ObjectId(24 * '1')
        self.create_user(user_id, roles=(), token='token')

        user_doc = self.get(f'/api/users/{user_id}', auth_token='token').get_json()
        self.assertNotIn('roles', user_doc)

        self.put(f'/api/users/{user_id}',
                 auth_token='token',
                 json=remove_private_keys(user_doc),
                 etag=user_doc['_etag'])
