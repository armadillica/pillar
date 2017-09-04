from pillar.tests import AbstractPillarTest


class AbstractPatchCommentTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        AbstractPillarTest.setUp(self, **kwargs)

        self.project_id, proj = self.ensure_project_exists()
        admin_group_id = proj['permissions']['groups'][0]['group']

        self.user_id = self.create_user(user_id=24 * 'a')
        self.owner_id = self.create_user(user_id=24 * 'b', groups=[admin_group_id])
        self.create_valid_auth_token(self.user_id, 'token')
        self.create_valid_auth_token(self.owner_id, 'owner-token')

        # Create a node to attach the comment to
        asset = {'description': '',
                 'project': self.project_id,
                 'node_type': 'asset',
                 'user': self.owner_id,
                 'properties': {'status': 'published'},
                 'name': 'Test asset'}

        resp = self.post('/api/nodes', json=asset,
                         auth_token='owner-token',
                         expected_status=201)
        self.asset_id = resp.json()['_id']

        # Create the comment
        comment = {'description': '',
                   'project': self.project_id,
                   'parent': self.asset_id,
                   'node_type': 'comment',
                   'user': self.owner_id,
                   'properties': {'rating_positive': 0,
                                  'rating_negative': 0,
                                  'status': 'published',
                                  'confidence': 0,
                                  'content': 'Purrrr kittycat',
                                  },
                   'name': 'Test comment'}

        resp = self.post('/api/nodes', json=comment,
                         auth_token='owner-token',
                         expected_status=201)
        comment_info = resp.json()
        self.node_url = '/api/nodes/%s' % comment_info['_id']


class VoteCommentTest(AbstractPatchCommentTest):
    def test_upvote_self_comment(self):
        # It should fail since we don't allow users to vote on own comment.
        self.patch(self.node_url,
                   json={'op': 'upvote'},
                   auth_token='owner-token',
                   expected_status=403)

    def test_downvote_self_comment(self):
        # It should fail since we don't allow users to vote on own comment.
        self.patch(self.node_url,
                   json={'op': 'downvote'},
                   auth_token='owner-token',
                   expected_status=403)

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
        self.assertEqual({'user': str(self.user_id), 'is_positive': True},
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
        self.assertEqual({'user': str(self.user_id), 'is_positive': False},
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
            {'user': str(other_user_ids[0]), 'is_positive': True},
            {'user': str(other_user_ids[1]), 'is_positive': True},
            {'user': str(other_user_ids[3]), 'is_positive': True},
            {'user': str(other_user_ids[4]), 'is_positive': False},
            {'user': str(self.user_id), 'is_positive': False},
        ], patched_node['properties'].get('ratings', []))


class EditCommentTest(AbstractPatchCommentTest):
    def test_comment_edit_happy(self, token='owner-token'):
        pre_node = self.get(self.node_url, auth_token=token).json()

        res = self.patch(self.node_url,
                         json={'op': 'edit', 'content': 'Je moeder is niet je vader.'},
                         auth_token=token).json()
        self.assertEqual('<p>Je moeder is niet je vader.</p>\n',
                         res['properties']['content_html'])

        # Get the node again, to inspect its changed state.
        patched_node = self.get(self.node_url, auth_token=token).json()
        self.assertEqual('Je moeder is niet je vader.',
                         patched_node['properties']['content'])
        self.assertEqual('<p>Je moeder is niet je vader.</p>\n',
                         patched_node['properties']['content_html'])
        self.assertNotEqual(pre_node['_etag'], patched_node['_etag'])

    def test_comment_edit_other_user_admin(self):
        admin_id = self.create_user(user_id=24 * 'c', roles={'admin'})
        self.create_valid_auth_token(admin_id, 'admin-token')

        self.test_comment_edit_happy(token='admin-token')

    def test_comment_edit_other_user_nonadmin(self):
        self.patch(self.node_url,
                   json={'op': 'edit', 'content': 'Je moeder is niet je vader.'},
                   auth_token='token',
                   expected_status=403)

        # Get the node again, to inspect its old state.
        patched_node = self.get(self.node_url, auth_token='token').json()
        self.assertEqual('Purrrr kittycat',
                         patched_node['properties']['content'])
        self.assertEqual('<p>Purrrr kittycat</p>\n',
                         patched_node['properties']['content_html'])

    def test_edit_noncomment_node(self):
        url = '/api/nodes/%s' % self.asset_id

        self.patch(url,
                   json={'op': 'edit', 'content': 'Je moeder is niet je vader.'},
                   auth_token='owner-token',
                   expected_status=405)

    def test_edit_nonexistant_node(self):
        url = '/api/nodes/%s' % ('0' * 24)

        self.patch(url,
                   json={'op': 'edit', 'content': 'Je moeder is niet je vader.'},
                   auth_token='owner-token',
                   expected_status=404)
