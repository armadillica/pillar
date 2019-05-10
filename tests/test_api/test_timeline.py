from datetime import timedelta, datetime

import bson
import flask

from pillar.tests import AbstractPillarTest


class GlobalTimelineTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        super().setUp(**kwargs)

        self.pid1, _ = self.ensure_project_exists()
        self.pid2, _ = self.ensure_project_exists(project_overrides={
            'name': 'Another Project',
            'url': 'another-url',

            '_id': bson.ObjectId('8572beecc0261b2005ed1a85'),
        })
        self.private_pid, _ = self.ensure_project_exists(project_overrides={
            '_id': '5672beecc0261b2005ed1a34',
            'is_private': True,
        })
        self.file_id, _ = self.ensure_file_exists(file_overrides={
            'variations': [
                {'format': 'mp4',
                 'duration': 3661  # 01:01:01
                 },
            ],
        })
        self.uid = self.create_user()

        self.fake_now = datetime.fromtimestamp(1521540308.0, tz=bson.tz_util.utc)  # A Tuesday

        self.all_asset_pid1_ids = [str(self.create_asset(self.pid1, i, 0)) for i in range(25)]
        self.all_asset_pid2_ids = [str(self.create_asset(self.pid2, i, 1)) for i in range(25)]
        self.all_asset_private_pid_ids = [str(self.create_asset(self.private_pid, i, 2)) for i in range(25)]

        self.all_post_pid1_ids = [str(self.create_post(self.pid1, i, 3)) for i in range(25)]
        self.all_post_pid2_ids = [str(self.create_post(self.pid2, i, 4)) for i in range(25)]
        self.all_post_private_pid_ids = [str(self.create_post(self.private_pid, i, 5)) for i in range(25)]

    def test_timeline_latest(self):
        with self.app.app_context():
            url = flask.url_for('timeline.global_timeline')
            response = self.get(url).json
            timeline = response['groups']
            continue_from = response['continue_from']

            self.assertEqual(1520229908.0, continue_from)
            self.assertEqual(3, len(timeline))
            self.assertEqual('Week 11, 2018', timeline[1]['label'])
            self.assertEqual('Week 10, 2018', timeline[2]['label'])
            self.assertEqual('Unittest project', timeline[0]['groups'][0]['label'])
            self.assertEqual('Another Project', timeline[0]['groups'][1]['label'])
            self.assertEqual('/p/default-project/', timeline[0]['groups'][0]['url'])
            self.assertEqual('/p/another-url/', timeline[0]['groups'][1]['url'])

            # week 12
            week = timeline[0]
            self.assertEqual('Week 12, 2018', week['label'])
            proj_pid1 = week['groups'][0]

            expected_post_ids = self.all_post_pid1_ids[0:2]
            expected_asset_ids = self.all_asset_pid1_ids[0:2]
            self.assertProjectEquals(proj_pid1, 'Unittest project', '/p/default-project/',
                                     expected_post_ids, expected_asset_ids)

            proj_pid2 = week['groups'][1]
            expected_post_ids = self.all_post_pid2_ids[0:2]
            expected_asset_ids = self.all_asset_pid2_ids[0:2]
            self.assertProjectEquals(proj_pid2, 'Another Project', '/p/another-url/',
                                     expected_post_ids, expected_asset_ids)

            # week 11
            week = timeline[1]
            self.assertEqual('Week 11, 2018', week['label'])
            proj_pid1 = week['groups'][0]

            expected_post_ids = self.all_post_pid1_ids[2:9]
            expected_asset_ids = self.all_asset_pid1_ids[2:9]
            self.assertProjectEquals(proj_pid1, 'Unittest project', '/p/default-project/',
                                     expected_post_ids, expected_asset_ids)

            proj_pid2 = week['groups'][1]
            expected_post_ids = self.all_post_pid2_ids[2:9]
            expected_asset_ids = self.all_asset_pid2_ids[2:9]
            self.assertProjectEquals(proj_pid2, 'Another Project', '/p/another-url/',
                                     expected_post_ids, expected_asset_ids)

            # week 10
            week = timeline[2]
            self.assertEqual('Week 10, 2018', week['label'])
            proj_pid1 = week['groups'][0]

            expected_post_ids = self.all_post_pid1_ids[9:16]
            expected_asset_ids = self.all_asset_pid1_ids[9:16]
            self.assertProjectEquals(proj_pid1, 'Unittest project', '/p/default-project/',
                                     expected_post_ids, expected_asset_ids)

            proj_pid2 = week['groups'][1]
            expected_post_ids = self.all_post_pid2_ids[9:16]
            expected_asset_ids = self.all_asset_pid2_ids[9:16]
            self.assertProjectEquals(proj_pid2, 'Another Project', '/p/another-url/',
                                     expected_post_ids, expected_asset_ids)

    def test_timeline_continue_from(self):
        with self.app.app_context():
            url = flask.url_for('timeline.global_timeline')
            response = self.get(url + '?from=1520229908.0').json
            timeline = response['groups']

            self.assertNotIn('continue_from', response)
            self.assertEqual(2, len(timeline))
            self.assertEqual('Week 9, 2018', timeline[0]['label'])
            self.assertEqual('Week 8, 2018', timeline[1]['label'])
            self.assertEqual('Unittest project', timeline[0]['groups'][0]['label'])
            self.assertEqual('Another Project', timeline[0]['groups'][1]['label'])
            self.assertEqual('/p/default-project/', timeline[0]['groups'][0]['url'])

            # week 9
            week = timeline[0]
            self.assertEqual('Week 9, 2018', week['label'])
            proj_pid1 = week['groups'][0]

            expected_post_ids = self.all_post_pid1_ids[16:23]
            expected_asset_ids = self.all_asset_pid1_ids[16:23]
            self.assertProjectEquals(proj_pid1, 'Unittest project', '/p/default-project/',
                                     expected_post_ids, expected_asset_ids)

            proj_pid2 = week['groups'][1]
            expected_post_ids = self.all_post_pid2_ids[16:23]
            expected_asset_ids = self.all_asset_pid2_ids[16:23]
            self.assertProjectEquals(proj_pid2, 'Another Project', '/p/another-url/',
                                     expected_post_ids, expected_asset_ids)

            # week 8
            week = timeline[1]
            self.assertEqual('Week 8, 2018', week['label'])
            proj_pid1 = week['groups'][0]

            expected_post_ids = self.all_post_pid1_ids[23:25]
            expected_asset_ids = self.all_asset_pid1_ids[23:25]
            self.assertProjectEquals(proj_pid1, 'Unittest project', '/p/default-project/',
                                     expected_post_ids, expected_asset_ids)

            proj_pid2 = week['groups'][1]
            expected_post_ids = self.all_post_pid2_ids[23:25]
            expected_asset_ids = self.all_asset_pid2_ids[23:25]
            self.assertProjectEquals(proj_pid2, 'Another Project', '/p/another-url/',
                                     expected_post_ids, expected_asset_ids)

    def assertProjectEquals(self, proj, label, url, expected_post_ids, expected_asset_ids):
        self.assertEqual(label, proj['label'])
        self.assertEqual(url, proj['url'])

        actual_ids = [n['_id'] for n in proj['items']['post']]
        self.assertEqual(expected_post_ids, actual_ids)

        actual_ids = [n['_id'] for n in proj['items']['asset']]
        self.assertEqual(expected_asset_ids, actual_ids)

    def create_asset(self, pid, days, hours):
        asset_node = {
            'name': 'Just a node name',
            'description': '',
            'node_type': 'asset',
            'user': self.uid,
        }
        asset_props = {
            'status': 'published',
            'file': self.file_id,
            'content_type': 'video',
            'order': 0
        }
        return self.create_node({
            **asset_node,
            'project': pid,
            '_created': self.fake_now - timedelta(days=days, hours=hours),
            'properties': asset_props,
        })

    def create_post(self, pid, days, hours):
        post_node = {
            'name': 'Just a node name',
            'description': '',
            'node_type': 'post',
            'user': self.uid,
        }
        post_props = {
            'status': 'published',
            'content': 'blablabla',
            'order': 0
        }
        return self.create_node({
            **post_node,
            'project': pid,
            '_created': self.fake_now - timedelta(days=days, hours=hours),
            'properties': post_props,
        })
