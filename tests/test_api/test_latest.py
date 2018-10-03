from datetime import timedelta

import flask

from pillar.tests import AbstractPillarTest


class LatestAssetsTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        super().setUp(**kwargs)

        self.pid, _ = self.ensure_project_exists()
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

        from pillar.api.utils import utcnow
        self.fake_now = utcnow()

    def test_latest_assets_returns_12_newest_assets(self):
        base_node = {
            'name': 'Just a node name',
            'project': self.pid,
            'description': '',
            'node_type': 'asset',
            'user': self.uid,
        }
        base_props = {
            'status': 'published',
            'file': self.file_id,
            'content_type': 'video',
            'order': 0
        }

        def create_asset(weeks):
            return self.create_node({
                **base_node,
                '_created': self.fake_now - timedelta(weeks=weeks),
                'properties': base_props,
            })

        all_asset_ids = [str(create_asset(i)) for i in range(20)]
        expected_ids = all_asset_ids[:12] # The 12 newest assets are expected


        with self.app.app_context():
            url = flask.url_for('latest.latest_assets')
            latest_assets = self.get(url).json['_items']

            actual_ids = [asset['_id'] for asset in latest_assets]
            self.assertListEqual(
                expected_ids, actual_ids)

    def test_latest_assets_ignore(self):
        base_node = {
            'name': 'Just a node name',
            'project': self.pid,
            'description': '',
            'node_type': 'asset',
            'user': self.uid,
        }
        base_props = {
            'status': 'published',
            'file': self.file_id,
            'content_type': 'video',
            'order': 0
        }

        ok_id = self.create_node({
            **base_node,
            '_created': self.fake_now - timedelta(seconds=1),
            'properties': base_props,
        })

        # Private should be ignored
        self.create_node({
            **base_node,
            '_created': self.fake_now - timedelta(seconds=1),
            'properties': base_props,
            'project': self.private_pid,
        })

        # Deleted should be ignored
        self.create_node({
            **base_node,
            '_deleted': True,
            '_created': self.fake_now - timedelta(seconds=1),
            'properties': base_props,
        })

        # Node type comment should be ignored
        self.create_node({
            '_created': self.fake_now - timedelta(seconds=1),
            'properties': base_props,
            'name': 'Just a node name',
            'project': self.pid,
            'description': '',
            'node_type': 'comment',
            'user': self.uid,
        })

        with self.app.app_context():
            url = flask.url_for('latest.latest_assets')
            latest_assets = self.get(url).json['_items']

            expected_ids = [str(ok_id)]
            actual_ids = [asset['_id'] for asset in latest_assets]
            self.assertListEqual(
                expected_ids, actual_ids)

    def test_latest_assets_data(self):
        base_node = {
            'name': 'Just a node name',
            'project': self.pid,
            'description': '',
            'node_type': 'asset',
            'user': self.uid,
        }
        base_props = {
            'status': 'published',
            'file': self.file_id,
            'content_type': 'video',
            'order': 0
        }

        ok_id = self.create_node({
            **base_node,
            '_created': self.fake_now - timedelta(seconds=1),
            'properties': base_props,
        })

        with self.app.app_context():
            url = flask.url_for('latest.latest_assets')
            latest_assets = self.get(url).json['_items']

            asset = latest_assets[0]
            self.assertEquals(str(ok_id), asset['_id'])
            self.assertEquals('Just a node name', asset['name'])


class LatestCommentsTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        super().setUp(**kwargs)

        self.pid, _ = self.ensure_project_exists()
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

        from pillar.api.utils import utcnow
        self.fake_now = utcnow()

        base_props = {
            'status': 'published',
            'file': self.file_id,
            'content_type': 'video',
            'order': 0
        }

        self.asset_node_id = self.create_node({
            'name': 'Just a node name',
            'project': self.pid,
            'description': '',
            'node_type': 'asset',
            'user': self.uid,
            '_created': self.fake_now - timedelta(weeks=52),
            'properties': base_props,
        })

    def test_latest_comments_returns_10_newest_comments(self):
        base_node = {
            'name': 'Comment',
            'project': self.pid,
            'description': '',
            'node_type': 'comment',
            'user': self.uid,
            'parent': self.asset_node_id,
        }
        base_props = {
            'status': 'published',
            'content': 'एनिमेशन is animation in Hindi',
        }

        def create_comment(weeks):
            return self.create_node({
                **base_node,
                '_created': self.fake_now - timedelta(weeks=weeks),
                'properties': base_props,
            })

        all_comment_ids = [str(create_comment(i)) for i in range(20)]
        expected_ids = all_comment_ids[:10]  # The 10 newest comments are expected

        with self.app.app_context():
            url = flask.url_for('latest.latest_comments')
            latest_assets = self.get(url).json['_items']

            actual_ids = [asset['_id'] for asset in latest_assets]
            self.assertListEqual(
                expected_ids, actual_ids)

    def test_latest_comments_ignore(self):
        base_node = {
            'name': 'Comment',
            'project': self.pid,
            'description': '',
            'node_type': 'comment',
            'user': self.uid,
            'parent': self.asset_node_id,
        }
        base_props = {
            'status': 'published',
            'content': 'एनिमेशन is animation in Hindi',
        }

        ok_id = self.create_node({
            **base_node,
            '_created': self.fake_now - timedelta(seconds=1),
            'properties': base_props,
        })

        # Private should be ignored
        self.create_node({
            **base_node,
            '_created': self.fake_now - timedelta(seconds=1),
            'properties': base_props,
            'project': self.private_pid,
        })

        # Deleted should be ignored
        self.create_node({
            **base_node,
            '_deleted': True,
            '_created': self.fake_now - timedelta(seconds=1),
            'properties': base_props,
        })

        # Node type asset should be ignored
        self.create_node({
            '_created': self.fake_now - timedelta(seconds=1),
            'properties': base_props,
            'name': 'Just a node name',
            'project': self.pid,
            'description': '',
            'node_type': 'asset',
            'user': self.uid,
        })

        with self.app.app_context():
            url = flask.url_for('latest.latest_comments')
            latest_comments = self.get(url).json['_items']

            expected_ids = [str(ok_id)]
            actual_ids = [comment['_id'] for comment in latest_comments]
            self.assertListEqual(
                expected_ids, actual_ids)

    def test_latest_comments_data(self):
        base_node = {
            'name': 'Comment',
            'project': self.pid,
            'description': '',
            'node_type': 'comment',
            'user': self.uid,
            'parent': self.asset_node_id,
        }
        base_props = {
            'status': 'published',
            'content': 'एनिमेशन is animation in Hindi',
        }

        ok_id = self.create_node({
            **base_node,
            '_created': self.fake_now - timedelta(seconds=1),
            'properties': base_props,
        })

        with self.app.app_context():
            url = flask.url_for('latest.latest_comments')
            latest_comments = self.get(url).json['_items']

            comment = latest_comments[0]
            self.assertEquals(str(ok_id), comment['_id'])
            self.assertEquals('Comment', comment['name'])
            self.assertEquals('एनिमेशन is animation in Hindi', comment['properties']['content'])
