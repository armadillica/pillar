import typing

from bson import ObjectId
import flask

from pillar.tests import AbstractPillarTest


class BreadcrumbsTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        super().setUp(**kwargs)
        self.project_id, self.project = self.ensure_project_exists()

    def _create_group(self,
                      parent_id: typing.Optional[ObjectId],
                      name: str) -> ObjectId:
        node = {
            'name': name,
            'description': '',
            'node_type': 'group',
            'user': self.project['user'],
            'properties': {'status': 'published'},
            'project': self.project_id,
        }
        if parent_id:
            node['parent'] = parent_id
        return self.create_node(node)

    def test_happy(self) -> ObjectId:
        # Create the nodes we expect to be returned in the breadcrumbs.
        top_group_node_id = self._create_group(None, 'Top-level node')
        group_node_id = self._create_group(top_group_node_id, 'Group node')

        fid, _ = self.ensure_file_exists()
        node_id = self.create_node({
            'name': 'Asset node',
            'parent': group_node_id,
            'description': '',
            'node_type': 'asset',
            'user': self.project['user'],
            'properties': {'status': 'published', 'file': fid},
            'project': self.project_id,
        })

        # Create some siblings that should not be returned.
        self._create_group(None, 'Sibling of top node')
        self._create_group(top_group_node_id, 'Sibling of group node')
        self._create_group(group_node_id, 'Sibling of asset node')

        expected = {'breadcrumbs': [
            {'_id': str(top_group_node_id),
             'name': 'Top-level node',
             'node_type': 'group',
             'url': f'/p/{self.project["url"]}/{top_group_node_id}'},
            {'_id': str(group_node_id),
             'name': 'Group node',
             'node_type': 'group',
             'url': f'/p/{self.project["url"]}/{group_node_id}'},
            {'_id': str(node_id),
             '_self': True,
             'name': 'Asset node',
             'node_type': 'asset',
             'url': f'/p/{self.project["url"]}/{node_id}'},
        ]}

        with self.app.app_context():
            url = flask.url_for('nodes.breadcrumbs', node_id=str(node_id))

        actual = self.get(url).json
        self.assertEqual(expected, actual)

        return node_id

    def test_missing_parent(self):
        # Note that this group node doesn't exist in the database:
        group_node_id = ObjectId(3 * 'deadbeef')

        fid, _ = self.ensure_file_exists()
        node_id = self.create_node({
            'name': 'Asset node',
            'parent': group_node_id,
            'description': '',
            'node_type': 'asset',
            'user': self.project['user'],
            'properties': {'status': 'published', 'file': fid},
            'project': self.project_id,
        })

        expected = {'breadcrumbs': [
            {'_id': str(group_node_id),
             '_exists': False,
             'name': '-unknown-'},
            {'_id': str(node_id),
             '_self': True,
             'name': 'Asset node',
             'node_type': 'asset',
             'url': f'/p/{self.project["url"]}/{node_id}'},
        ]}

        with self.app.app_context():
            url = flask.url_for('nodes.breadcrumbs', node_id=str(node_id))

        actual = self.get(url).json
        self.assertEqual(expected, actual)

    def test_missing_node(self):
        with self.app.app_context():
            url = flask.url_for('nodes.breadcrumbs', node_id=3 * 'deadbeef')
        self.get(url, expected_status=404)

    def test_permissions(self):
        # Use the same test case as the happy case.
        node_id = self.test_happy()

        # Tweak the project to make it private.
        with self.app.app_context():
            proj_coll = self.app.db('projects')
            result = proj_coll.update_one({'_id': self.project_id},
                                          {'$set': {'permissions.world': []}})
            self.assertEqual(1, result.modified_count)
            self.project = self.fetch_project_from_db(self.project_id)

        with self.app.app_context():
            url = flask.url_for('nodes.breadcrumbs', node_id=str(node_id))

        # Anonymous access should be forbidden.
        self.get(url, expected_status=403)

        # Authorized access should work, though.
        self.create_valid_auth_token(self.project['user'], token='user-token')
        self.get(url, auth_token='user-token')
