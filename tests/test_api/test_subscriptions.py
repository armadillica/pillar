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

    def _setup_testcase(self, mocked_fetch_blenderid_user, *,
                        store_says_cloud_access: bool,
                        bid_says_cloud_demo: bool):
        import urllib.parse
        url = '%s?blenderid=%s' % (self.app.config['EXTERNAL_SUBSCRIPTIONS_MANAGEMENT_SERVER'],
                                   urllib.parse.quote(TEST_EMAIL_ADDRESS))
        responses.add('GET', url,
                      json={'shop_id': 58432,
                            'cloud_access': 1 if store_says_cloud_access else 0,
                            'paid_balance': 0,
                            'balance_currency': 'EUR',
                            'start_date': '2017-05-04 12:07:49',
                            'expiration_date': '2017-08-04 10:07:49',
                            'subscription_status': 'wc-active'
                            },
                      status=200,
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
        if bid_says_cloud_demo:
            mocked_fetch_blenderid_user.return_value['roles']['cloud_demo'] = True

    @responses.activate
    @mock.patch('pillar.api.blender_id.fetch_blenderid_user')
    def test_store_api_role_grant_subscriber(self, mocked_fetch_blenderid_user):
        self._setup_testcase(mocked_fetch_blenderid_user,
                             store_says_cloud_access=True,
                             bid_says_cloud_demo=False)

        self.get('/api/bcloud/update-subscription', auth_token='my-happy-token',
                 expected_status=204)
        user_info = self.get('/api/users/me', auth_token='my-happy-token').json()
        self.assertEqual(['subscriber'], user_info['roles'])

    @responses.activate
    @mock.patch('pillar.api.blender_id.fetch_blenderid_user')
    def test_store_api_role_revoke_subscriber(self, mocked_fetch_blenderid_user):
        self._setup_testcase(mocked_fetch_blenderid_user,
                             store_says_cloud_access=False,
                             bid_says_cloud_demo=False)

        # Make sure this user is currently known as a subcriber.
        self.create_user(roles={'subscriber'}, token='my-happy-token')
        user_info = self.get('/api/users/me', auth_token='my-happy-token').json()
        self.assertEqual(['subscriber'], user_info['roles'])

        # And after updating, it shouldn't be.
        self.get('/api/bcloud/update-subscription', auth_token='my-happy-token',
                 expected_status=204)
        user_info = self.get('/api/users/me', auth_token='my-happy-token').json()
        self.assertEqual([], user_info['roles'])

    @responses.activate
    @mock.patch('pillar.api.blender_id.fetch_blenderid_user')
    def test_bid_api_grant_demo(self, mocked_fetch_blenderid_user):
        self._setup_testcase(mocked_fetch_blenderid_user,
                             store_says_cloud_access=False,
                             bid_says_cloud_demo=True)

        self.get('/api/bcloud/update-subscription', auth_token='my-happy-token',
                 expected_status=204)

        user_info = self.get('/api/users/me', auth_token='my-happy-token').json()
        self.assertEqual(['demo'], user_info['roles'])

    @responses.activate
    @mock.patch('pillar.api.blender_id.fetch_blenderid_user')
    def test_bid_api_role_revoke_subscriber(self, mocked_fetch_blenderid_user):
        self._setup_testcase(mocked_fetch_blenderid_user,
                             store_says_cloud_access=False,
                             bid_says_cloud_demo=False)

        # Make sure this user is currently known as demo user.
        self.create_user(roles={'demo'}, token='my-happy-token')
        user_info = self.get('/api/users/me', auth_token='my-happy-token').json()
        self.assertEqual(['demo'], user_info['roles'])

        # And after updating, it shouldn't be.
        self.get('/api/bcloud/update-subscription', auth_token='my-happy-token',
                 expected_status=204)
        user_info = self.get('/api/users/me', auth_token='my-happy-token').json()
        self.assertEqual([], user_info['roles'])
