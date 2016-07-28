from common_test_class import AbstractPillarTest
import common_test_data as ctd


class PatchCommentTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        AbstractPillarTest.setUp(self, **kwargs)

        self.user_id = self.create_user(user_id=24 * 'a')
        self.owner_id = self.create_user(user_id=24 * 'b')
        self.create_valid_auth_token(self.user_id, 'token')
        self.create_valid_auth_token(self.owner_id, 'owner-token')
        self.project_id, _ = self.ensure_project_exists()

        comment = {'description': '',
                   'project': self.project_id,
                   'node_type': 'comment',
                   'user': self.owner_id,
                   'properties': {'rating_positive': 0,
                                  'rating_negative': 0,
                                  'status': 'published',
                                  'confidence': 0,
                                  'content': 'Purrrr kittycat',
                                  },
                   'name': 'Test comment'}

        # Use MongoDB to insert the node (comments aren't allowed to be parentless,
        # so Eve would bark).
        with self.app.test_request_context():
            nodes_coll = self.app.data.driver.db['nodes']
            result = nodes_coll.insert_one(comment)
            self.assertIsNotNone(result.inserted_id)
            comment_id = result.inserted_id

        self.node_url = '/nodes/%s' % comment_id

    def test_upvote_other_comment(self):
        # Patch the node
        res = self.patch(self.node_url,
                         json={'op': 'upvote'},
                         auth_token='token').json()
        self.assertEqual(1, res['properties']['rating_positive'])
        self.assertEqual(0, res['properties']['rating_negative'])

        # Get the node again, to inspect its changed state.
        patched_node = self.get(self.node_url, auth_token='token').json()
        self.assertEqual(1, patched_node['properties']['rating_positive'])
        self.assertEqual(0, patched_node['properties']['rating_negative'])
        self.assertEqual({u'user': str(self.user_id), u'is_positive': True},
                         patched_node['properties']['ratings'][0])
        self.assertEqual(1, len(patched_node['properties']['ratings']))

    def test_upvote_twice(self):
        # Both tests check for rating_positive=1
        self.test_upvote_other_comment()
        self.test_upvote_other_comment()

    def test_downvote_other_comment(self):
        # Patch the node
        res = self.patch(self.node_url,
                         json={'op': 'downvote'},
                         auth_token='token').json()
        self.assertEqual(0, res['properties']['rating_positive'])
        self.assertEqual(1, res['properties']['rating_negative'])

        # Get the node again, to inspect its changed state.
        patched_node = self.get(self.node_url, auth_token='token').json()
        self.assertEqual(0, patched_node['properties']['rating_positive'])
        self.assertEqual(1, patched_node['properties']['rating_negative'])
        self.assertEqual({u'user': str(self.user_id), u'is_positive': False},
                         patched_node['properties']['ratings'][0])
        self.assertEqual(1, len(patched_node['properties']['ratings']))

    def test_downvote_twice(self):
        # Both tests check for rating_negative=1
        self.test_downvote_other_comment()
        self.test_downvote_other_comment()

    def test_up_then_downvote(self):
        self.test_upvote_other_comment()
        self.test_downvote_other_comment()

    def test_down_then_upvote(self):
        self.test_downvote_other_comment()
        self.test_upvote_other_comment()

    def test_down_then_up_then_downvote(self):
        self.test_downvote_other_comment()
        self.test_upvote_other_comment()
        self.test_downvote_other_comment()

    def test_revoke_noop(self):
        # Patch the node
        self.patch(self.node_url,
                   json={'op': 'revoke'},
                   auth_token='token')

        # Get the node again, to inspect its changed state.
        patched_node = self.get(self.node_url, auth_token='token').json()
        self.assertEqual(0, patched_node['properties']['rating_positive'])
        self.assertEqual(0, patched_node['properties']['rating_negative'])
        self.assertEqual([], patched_node['properties'].get('ratings', []))

    def test_revoke_upvote(self):
        self.test_upvote_other_comment()
        self.test_revoke_noop()

    def test_revoke_downvote(self):
        self.test_downvote_other_comment()
        self.test_revoke_noop()

    def test_with_other_users(self):
        # Generate a bunch of users
        other_user_ids = []
        for idx in range(5):
            uid = self.create_user(user_id=24 * str(idx))
            other_user_ids.append(uid)
            self.create_valid_auth_token(uid, 'other-token-%i' % idx)

        # Let them all vote positive.
        for idx in range(5):
            self.patch(self.node_url,
                       json={'op': 'upvote'},
                       auth_token='other-token-%i' % idx)

        # Use our standard user to downvote (the negative nancy)
        self.patch(self.node_url,
                   json={'op': 'downvote'},
                   auth_token='token')

        # Let one of the other users revoke
        self.patch(self.node_url,
                   json={'op': 'revoke'},
                   auth_token='other-token-2')

        # And another user downvotes to override their previous upvote
        self.patch(self.node_url,
                   json={'op': 'downvote'},
                   auth_token='other-token-4')

        # Inspect the result
        patched_node = self.get(self.node_url, auth_token='token').json()
        self.assertEqual(3, patched_node['properties']['rating_positive'])
        self.assertEqual(2, patched_node['properties']['rating_negative'])
        self.assertEqual([
            {u'user': unicode(other_user_ids[0]), u'is_positive': True},
            {u'user': unicode(other_user_ids[1]), u'is_positive': True},
            {u'user': unicode(other_user_ids[3]), u'is_positive': True},
            {u'user': unicode(other_user_ids[4]), u'is_positive': False},
            {u'user': unicode(self.user_id), u'is_positive': False},
        ], patched_node['properties'].get('ratings', []))
