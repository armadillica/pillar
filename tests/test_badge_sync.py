import datetime

import requests
import responses

from pillar.tests import AbstractPillarTest

httpmock = responses.RequestsMock()


class AbstractSyncTest(AbstractPillarTest):
    def setUp(self):
        super().setUp()
        self.uid1 = self.create_user(24 * '1')
        self.uid2 = self.create_user(24 * '2')

        # Make sure the users have different auth info.
        with self.app.app_context():
            users_coll = self.app.db('users')
            users_coll.update_one(
                {'_id': self.uid1},
                {'$set': {'auth': [
                    {'provider': 'local', 'user_id': '47', 'token': ''},
                    {'provider': 'blender-id', 'user_id': '1947', 'token': ''},
                ]}})
            users_coll.update_one(
                {'_id': self.uid2},
                {'$set': {'auth': [
                    {'provider': 'blender-id', 'user_id': '4488', 'token': ''},
                    {'provider': 'local', 'user_id': '48', 'token': ''},
                ]}})

        self.create_valid_auth_token(self.uid1, token='find-this-token-uid1',
                                     oauth_scopes=['email', 'badge'])
        self.create_valid_auth_token(self.uid1, token='no-badge-scope',
                                     oauth_scopes=['email'])
        self.create_valid_auth_token(self.uid1, token='expired',
                                     oauth_scopes=['email', 'badge'],
                                     expire_in_days=-1)

        self.create_valid_auth_token(self.uid2, token='find-this-token-uid2',
                                     oauth_scopes=['email', 'badge'])
        self.create_valid_auth_token(self.uid2, token='no-badge-scope',
                                     oauth_scopes=['email'])
        self.create_valid_auth_token(self.uid2, token='expired',
                                     oauth_scopes=['email', 'badge'],
                                     expire_in_days=-1)

        from pillar import badge_sync
        self.sync_user1 = badge_sync.SyncUser(self.uid1, 'find-this-token-uid1', '1947')
        self.sync_user2 = badge_sync.SyncUser(self.uid2, 'find-this-token-uid2', '4488')


class FindUsersToSyncTest(AbstractSyncTest):
    def test_no_badge_fetched_yet(self):
        from pillar import badge_sync
        with self.app.app_context():
            found = set(badge_sync.find_users_to_sync())
        self.assertEqual({self.sync_user1, self.sync_user2}, found)

    def _update_badge_expiry(self, delta_minutes1, delta_minutes2):
        """Make badges of userN expire in delta_minutesN minutes."""
        from pillar.api.utils import utcnow, remove_private_keys
        now = utcnow()

        # Do the update via Eve so that that flow is covered too.
        users_coll = self.app.db('users')
        db_user1 = users_coll.find_one(self.uid1)
        db_user1['badges'] = {
            'html': 'badge for user 1',
            'expires': now + datetime.timedelta(minutes=delta_minutes1)
        }
        r, _, _, status = self.app.put_internal('users',
                                                remove_private_keys(db_user1),
                                                _id=self.uid1)
        self.assertEqual(200, status, r)

        db_user2 = users_coll.find_one(self.uid2)
        db_user2['badges'] = {
            'html': 'badge for user 2',
            'expires': now + datetime.timedelta(minutes=delta_minutes2)
        }
        r, _, _, status = self.app.put_internal('users',
                                                remove_private_keys(db_user2),
                                                _id=self.uid2)
        self.assertEqual(200, status, r)

    def test_badge_fetched_recently(self):
        from pillar import badge_sync

        # Badges of user1 expired, user2 didn't yet.
        with self.app.app_context():
            self._update_badge_expiry(-5, 5)
            found = list(badge_sync.find_users_to_sync())
        self.assertEqual([self.sync_user1], found)

        # Badges of both users expired, but user2 expired longer ago.
        with self.app.app_context():
            self._update_badge_expiry(-5, -10)
            found = list(badge_sync.find_users_to_sync())
        self.assertEqual([self.sync_user2, self.sync_user1], found)

        # Badges of both not expired yet.
        with self.app.app_context():
            self._update_badge_expiry(2, 3)
            found = list(badge_sync.find_users_to_sync())
        self.assertEqual([], found)


class FetchHTMLTest(AbstractSyncTest):
    @httpmock.activate
    def test_happy(self):
        from pillar import badge_sync
        from pillar.api.utils import utcnow

        def check_request(request: requests.PreparedRequest):
            if request.headers['Authorization'] != 'Bearer find-this-token-uid1':
                return 403, {}, 'BAD TOKEN'
            return 200, {'Content-Type': 'text/html; charset=utf-8'}, 'твоја мајка'.encode()

        httpmock.add_callback('GET', 'http://id.local:8001/api/badges/1947/html/s', check_request)

        with self.app.app_context():
            badge_html = badge_sync.fetch_badge_html(requests.Session(), self.sync_user1, 's')
            expected_expire = utcnow() + self.app.config['BLENDER_ID_BADGE_EXPIRY']

        self.assertEqual('твоја мајка', badge_html.html)
        margin = datetime.timedelta(minutes=1)
        self.assertLess(expected_expire - margin, badge_html.expires)
        self.assertGreater(expected_expire + margin, badge_html.expires)

    @httpmock.activate
    def test_internal_server_error(self):
        from pillar import badge_sync

        httpmock.add('GET', 'http://id.local:8001/api/badges/1947/html/s',
                     body='oops', status=500)

        with self.assertRaises(badge_sync.StopRefreshing), self.app.app_context():
            badge_sync.fetch_badge_html(requests.Session(), self.sync_user1, 's')

    @httpmock.activate
    def test_no_badge(self):
        from pillar import badge_sync

        httpmock.add('GET', 'http://id.local:8001/api/badges/1947/html/s',
                     body='', status=204)
        with self.app.app_context():
            badge_html = badge_sync.fetch_badge_html(requests.Session(), self.sync_user1, 's')
        self.assertIsNone(badge_html)

    @httpmock.activate
    def test_no_such_user(self):
        from pillar import badge_sync

        httpmock.add('GET', 'http://id.local:8001/api/badges/1947/html/s',
                     body='Not Found', status=404)
        with self.app.app_context():
            badge_html = badge_sync.fetch_badge_html(requests.Session(), self.sync_user1, 's')
        self.assertIsNone(badge_html)

    @httpmock.activate
    def test_no_connection_possible(self):
        from pillar import badge_sync

        with self.assertRaises(badge_sync.StopRefreshing), self.app.app_context():
            badge_sync.fetch_badge_html(requests.Session(), self.sync_user1, 's')


class RefreshAllTest(AbstractSyncTest):
    @httpmock.activate
    def test_happy(self):
        from pillar import badge_sync

        httpmock.add('GET', 'http://id.local:8001/api/badges/1947/html/s',
                     body='badges for Agent 47')
        httpmock.add('GET', 'http://id.local:8001/api/badges/4488/html/s',
                     body='badges for that other user')

        with self.app.app_context():
            badge_sync.refresh_all_badges(timelimit=datetime.timedelta(seconds=4))

        db_user1 = self.get('/api/users/me', auth_token=self.sync_user1.token).json
        db_user2 = self.get('/api/users/me', auth_token=self.sync_user2.token).json
        self.assertEqual('badges for Agent 47', db_user1['badges']['html'])
        self.assertEqual('badges for that other user', db_user2['badges']['html'])

    @httpmock.activate
    def test_timelimit(self):
        from pillar import badge_sync

        # This shouldn't hit any connection error, because it should immediately
        # hit the time limit, before doing any call to Blender ID.
        with self.app.app_context():
            badge_sync.refresh_all_badges(timelimit=datetime.timedelta(seconds=-4))
