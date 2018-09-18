from unittest import mock

import bson
from eve import RFC1123_DATE_FORMAT
import flask

from pillar.tests import AbstractPillarTest


class AbstractVideoProgressTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        super().setUp(**kwargs)

        self.pid, _ = self.ensure_project_exists()

        self.admin_uid = self.create_user(24 * 'a', roles={'admin'})
        self.uid = self.create_user(24 * 'b', roles={'subscriber'})

        from pillar.api.utils import utcnow
        self.fake_now = utcnow()
        self.fake_now_str = self.fake_now.strftime(RFC1123_DATE_FORMAT)

    def create_video_node(self) -> bson.ObjectId:
        return self.create_node({
            'description': '',
            'node_type': 'asset',
            'user': self.admin_uid,
            'properties': {
                'status': 'published',
                'content_type': 'video',
                'file': bson.ObjectId()},
            'name': 'Image test',
            'project': self.pid,
        })

    def set_progress(self,
                     progress_in_sec: float = 413.0,
                     progress_in_perc: int = 65,
                     expected_status: int = 204) -> None:
        with self.login_as(self.uid):
            url = flask.url_for('users_api.set_video_progress', video_id=str(self.video_id))
            self.post(url,
                      data={'progress_in_sec': progress_in_sec,
                            'progress_in_perc': progress_in_perc},
                      expected_status=expected_status)

    def get_progress(self, expected_status: int = 200) -> dict:
        with self.login_as(self.uid):
            url = flask.url_for('users_api.get_video_progress', video_id=str(self.video_id))
            progress = self.get(url, expected_status=expected_status)
        return progress.json

    def create_video_and_set_progress(self, progress_in_sec=413.0, progress_in_perc=65):
        self.video_id = self.create_video_node()

        # Check that we can get the progress after setting it.
        with mock.patch('pillar.api.utils.utcnow') as utcnow:
            utcnow.return_value = self.fake_now
            self.set_progress(progress_in_sec, progress_in_perc)


class HappyFlowVideoProgressTest(AbstractVideoProgressTest):

    def test_video_progress_known_video(self):
        self.create_video_and_set_progress()
        progress = self.get_progress()

        expected_progress = {
            'progress_in_sec': 413.0,
            'progress_in_percent': 65,
            'last_watched': self.fake_now,
        }
        self.assertEqual({**expected_progress, 'last_watched': self.fake_now_str},
                         progress)

        # Check that the database has been updated correctly.
        self.db_user = self.fetch_user_from_db(self.uid)
        self.assertEqual({str(self.video_id): expected_progress},
                         self.db_user['nodes']['view_progress'])

    def test_user_adheres_to_schema(self):
        from pillar.api.utils import remove_private_keys
        # This check is necessary because the API code uses direct MongoDB manipulation,
        # which means that the user can end up not matching the Cerberus schema.
        self.create_video_and_set_progress()
        db_user = self.fetch_user_from_db(self.uid)

        r, _, _, status = self.app.put_internal(
            'users',
            payload=remove_private_keys(db_user),
            _id=db_user['_id'])
        self.assertEqual(200, status, r)

    def test_video_progress_is_private(self):
        self.create_video_and_set_progress()

        with self.login_as(self.uid):
            resp = self.get(f'/api/users/{self.uid}')
        self.assertIn('nodes', resp.json)

        other_uid = self.create_user(24 * 'c', roles={'subscriber'})
        with self.login_as(other_uid):
            resp = self.get(f'/api/users/{self.uid}')
        self.assertIn('username', resp.json)  # just to be sure this is a real user response
        self.assertNotIn('nodes', resp.json)

    def test_done_at_100_percent(self):
        self.create_video_and_set_progress(630, 100)
        progress = self.get_progress()
        self.assertEqual({'progress_in_sec': 630.0,
                          'progress_in_percent': 100,
                          'last_watched': self.fake_now_str,
                          'done': True},
                         progress)

    def test_done_at_95_percent(self):
        self.create_video_and_set_progress(599, 95)
        progress = self.get_progress()
        self.assertEqual({'progress_in_sec': 599.0,
                          'progress_in_percent': 95,
                          'last_watched': self.fake_now_str,
                          'done': True},
                         progress)

    def test_rewatch_after_done(self):
        from pillar.api.utils import utcnow

        self.create_video_and_set_progress(630, 100)

        # Re-watching should keep the 'done' key.
        another_fake_now = utcnow()
        with mock.patch('pillar.api.utils.utcnow') as mock_utcnow:
            mock_utcnow.return_value = another_fake_now
            self.set_progress(444, 70)

        progress = self.get_progress()
        self.assertEqual({'progress_in_sec': 444,
                          'progress_in_percent': 70,
                          'done': True,
                          'last_watched': another_fake_now.strftime(RFC1123_DATE_FORMAT)},
                         progress)

    def test_inconsistent_progress(self):
        # Send a percentage that's incorrect. It should just be copied.
        self.create_video_and_set_progress(413.557, 30)
        progress = self.get_progress()

        expected_progress = {
            'progress_in_sec': 413.557,
            'progress_in_percent': 30,
            'last_watched': self.fake_now,
        }
        self.assertEqual({**expected_progress, 'last_watched': self.fake_now_str},
                         progress)

        # Check that the database has been updated correctly.
        self.db_user = self.fetch_user_from_db(self.uid)
        self.assertEqual({str(self.video_id): expected_progress},
                         self.db_user['nodes']['view_progress'])


class UnhappyFlowVideoProgressTest(AbstractVideoProgressTest):
    def test_get_video_progress_invalid_video_id(self):
        with self.login_as(self.uid):
            url = flask.url_for('users_api.get_video_progress', video_id='jemoeder')
            self.get(url, expected_status=400)

    def test_get_video_progress_unknown_video(self):
        with self.login_as(self.uid):
            url = flask.url_for('users_api.get_video_progress', video_id=24 * 'f')
            self.get(url, expected_status=204)

    def test_set_video_progress_unknown_video(self):
        with self.login_as(self.uid):
            url = flask.url_for('users_api.set_video_progress', video_id=24 * 'f')
            self.post(url,
                      data={'progress_in_sec': 16, 'progress_in_perc': 10},
                      expected_status=404)

    def test_set_video_progress_invalid_video_id(self):
        with self.login_as(self.uid):
            url = flask.url_for('users_api.set_video_progress', video_id='jemoeder')
            self.post(url,
                      data={'progress_in_sec': 16, 'progress_in_perc': 10},
                      expected_status=400)

    def test_get_video_empty_dict(self):
        self.video_id = bson.ObjectId(24 * 'f')
        with self.app.app_context():
            users_coll = self.app.db('users')
            # The progress dict for that video is there, but empty.
            users_coll.update_one(
                {'_id': self.uid},
                {'$set': {f'nodes.view_progress.{self.video_id}': {}}})

        progress = self.get_progress(expected_status=204)
        self.assertIsNone(progress)

    def test_missing_post_field(self):
        with self.login_as(self.uid):
            url = flask.url_for('users_api.set_video_progress', video_id=24 * 'f')
            self.post(url, data={'progress_in_ms': 1000}, expected_status=400)

    def test_nonint_progress(self):
        with self.login_as(self.uid):
            url = flask.url_for('users_api.set_video_progress', video_id=24 * 'f')
            self.post(url, data={'progress_in_sec': 'je moeder'}, expected_status=400)

    def test_asset_is_valid_but_not_video(self):
        self.video_id = self.create_node({
            'description': '',
            'node_type': 'asset',
            'user': self.admin_uid,
            'properties': {
                'status': 'published',
                'content_type': 'image',  # instead of video
                'file': bson.ObjectId()},
            'name': 'Image test',
            'project': self.pid,
        })

        with mock.patch('pillar.api.utils.utcnow') as utcnow:
            utcnow.return_value = self.fake_now
            self.set_progress(expected_status=404)
        self.get_progress(expected_status=204)

    def test_asset_malformed(self):
        self.video_id = self.create_node({
            'description': '',
            'node_type': 'asset',
            'user': self.admin_uid,
            'properties': {
                'status': 'published',
                # Note the lack of a 'content_type' key.
                'file': bson.ObjectId()},
            'name': 'Missing content_type test',
            'project': self.pid,
        })

        with mock.patch('pillar.api.utils.utcnow') as utcnow:
            utcnow.return_value = self.fake_now
            self.set_progress(expected_status=404)
        self.get_progress(expected_status=204)
