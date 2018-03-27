from bson import ObjectId

from pillar.tests import AbstractPillarTest


class PurgeHomeProjectsTest(AbstractPillarTest):
    def test_purge(self):
        self.create_standard_groups()
        # user_a will be soft-deleted, user_b will be hard-deleted.
        # We don't support soft-deleting users yet, but the code should be
        # handling that properly anyway.
        user_a = self.create_user(user_id=24 * 'a', roles={'subscriber'}, token='token-a')
        user_b = self.create_user(user_id=24 * 'b', roles={'subscriber'}, token='token-b')

        # GET the home project to create it.
        home_a = self.get('/api/bcloud/home-project', auth_token='token-a').json()
        home_b = self.get('/api/bcloud/home-project', auth_token='token-b').json()

        with self.app.app_context():
            users_coll = self.app.db('users')

            res = users_coll.update_one({'_id': user_a}, {'$set': {'_deleted': True}})
            self.assertEqual(1, res.modified_count)

            res = users_coll.delete_one({'_id': user_b})
            self.assertEqual(1, res.deleted_count)

        from pillar.cli.maintenance import purge_home_projects

        with self.app.app_context():
            self.assertEqual(2, purge_home_projects(go=True))

            proj_coll = self.app.db('projects')
            self.assertEqual(True, proj_coll.find_one({'_id': ObjectId(home_a['_id'])})['_deleted'])
            self.assertEqual(True, proj_coll.find_one({'_id': ObjectId(home_b['_id'])})['_deleted'])
