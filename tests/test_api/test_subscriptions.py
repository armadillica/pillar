import typing
from unittest import mock

import responses

from pillar.tests import AbstractPillarTest, TEST_EMAIL_ADDRESS


# The OAuth lib doesn't use requests, so we can't use responses to mock it.
# Instead, we use unittest.mock for that.


class RoleUpdatingTest(AbstractPillarTest):
    def setUp(self):
        super().setUp()

        with self.app.test_request_context():
            self.create_standard_groups()

        from pillar.api.blender_cloud import subscription as sub
        self.user_subs_signal_calls = []
        sub.user_subscription_updated.connect(self._user_subs_signal)

    def _user_subs_signal(self, sender, **kwargs):
        self.user_subs_signal_calls.append((sender, kwargs))

    def _setup_testcase(self, mocked_fetch_blenderid_user, *,
                        bid_roles: typing.Set[str]):
        import urllib.parse

        # The Store API endpoint should not be called upon any more.
        url = '%s?blenderid=%s' % (self.app.config['EXTERNAL_SUBSCRIPTIONS_MANAGEMENT_SERVER'],
                                   urllib.parse.quote(TEST_EMAIL_ADDRESS))
        responses.add('GET', url,
                      status=500,
                      match_querystring=True)

        self.mock_blenderid_validate_happy()
        mocked_fetch_blenderid_user.return_value = {
            'email': TEST_EMAIL_ADDRESS,
            'full_name': 'dr. Sybren A. St\u00fcvel',
            'id': 5555,
            'roles': {
                'admin': True,
                'bfct_trainer': False,
                'conference_speaker': True,
                'network_member': True
            }
        }
        for role in bid_roles:
            mocked_fetch_blenderid_user.return_value['roles'][role] = True

    @responses.activate
    @mock.patch('pillar.api.blender_id.fetch_blenderid_user')
    def test_store_api_role_grant_subscriber(self, mocked_fetch_blenderid_user):
        self._setup_testcase(mocked_fetch_blenderid_user,
                             bid_roles={'cloud_subscriber', 'cloud_has_subscription'})

        self.get('/api/bcloud/update-subscription', auth_token='my-happy-token',
                 expected_status=204)
        user_info = self.get('/api/users/me', auth_token='my-happy-token').json()
        self.assertEqual({'subscriber', 'has_subscription'}, set(user_info['roles']))

        # Check the signals
        self.assertEqual(1, len(self.user_subs_signal_calls))
        sender, kwargs = self.user_subs_signal_calls[0]
        self.assertEqual({'revoke_roles': set(), 'grant_roles': {'subscriber', 'has_subscription'}},
                         kwargs)

    @responses.activate
    @mock.patch('pillar.api.blender_id.fetch_blenderid_user')
    def test_store_api_role_revoke_subscriber(self, mocked_fetch_blenderid_user):
        self._setup_testcase(mocked_fetch_blenderid_user,
                             bid_roles={'conference_speaker'})

        # Make sure this user is currently known as a subcriber.
        self.create_user(roles={'subscriber', 'has_subscription'}, token='my-happy-token')
        user_info = self.get('/api/users/me', auth_token='my-happy-token').json()
        self.assertEqual({'subscriber', 'has_subscription'}, set(user_info['roles']))

        # And after updating, it shouldn't be.
        self.get('/api/bcloud/update-subscription', auth_token='my-happy-token',
                 expected_status=204)
        user_info = self.get('/api/users/me', auth_token='my-happy-token').json()
        self.assertEqual([], user_info['roles'])

        self.assertEqual(1, len(self.user_subs_signal_calls))
        sender, kwargs = self.user_subs_signal_calls[0]
        self.assertEqual({'revoke_roles': {'subscriber', 'has_subscription'}, 'grant_roles': set()},
                         kwargs)

    @responses.activate
    @mock.patch('pillar.api.blender_id.fetch_blenderid_user')
    def test_bid_api_grant_demo(self, mocked_fetch_blenderid_user):
        self._setup_testcase(mocked_fetch_blenderid_user,
                             bid_roles={'cloud_demo'})

        self.get('/api/bcloud/update-subscription', auth_token='my-happy-token',
                 expected_status=204)

        user_info = self.get('/api/users/me', auth_token='my-happy-token').json()
        self.assertEqual(['demo'], user_info['roles'])

        self.assertEqual(1, len(self.user_subs_signal_calls))
        sender, kwargs = self.user_subs_signal_calls[0]
        self.assertEqual({'revoke_roles': set(), 'grant_roles': {'demo'}}, kwargs)

    @responses.activate
    @mock.patch('pillar.api.blender_id.fetch_blenderid_user')
    def test_bid_api_role_revoke_demo(self, mocked_fetch_blenderid_user):
        self._setup_testcase(mocked_fetch_blenderid_user,
                             bid_roles={'conference_speaker'})

        # Make sure this user is currently known as demo user.
        self.create_user(roles={'demo'}, token='my-happy-token')
        user_info = self.get('/api/users/me', auth_token='my-happy-token').json()
        self.assertEqual(['demo'], user_info['roles'])

        # And after updating, it shouldn't be.
        self.get('/api/bcloud/update-subscription', auth_token='my-happy-token',
                 expected_status=204)
        user_info = self.get('/api/users/me', auth_token='my-happy-token').json()
        self.assertEqual([], user_info['roles'])

        self.assertEqual(1, len(self.user_subs_signal_calls))
        sender, kwargs = self.user_subs_signal_calls[0]
        self.assertEqual({'revoke_roles': {'demo'}, 'grant_roles': set()}, kwargs)
