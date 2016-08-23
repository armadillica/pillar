"""Tests for the FlaskInternal SDK."""

from os.path import join, dirname, abspath, exists

from flask import url_for
import pillarsdk

from pillar.tests import AbstractPillarTest
from pillar.sdk import FlaskInternalApi

blender_desktop_logo_path = join(dirname(abspath(__file__)), 'BlenderDesktopLogo.png')
assert exists(blender_desktop_logo_path)


class FlaskInternalApiTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        AbstractPillarTest.setUp(self, **kwargs)

        self.project_id, self.user_id = self.create_project_with_admin()
        self.create_valid_auth_token(self.user_id, 'token')

        self.sdk_api = FlaskInternalApi(
            endpoint='/api/',
            username=None,
            password=None,
            token='token'
        )

    def test_create_asset(self):
        with self.app.test_request_context():
            asset = pillarsdk.Node({'description': '',
                                    'project': str(self.project_id),
                                    'node_type': 'asset',
                                    'user': str(self.user_id),
                                    'properties': {'status': 'published',
                                                   'content_type': 'je moeder'},
                                    'name': 'Test asset'})
            created_ok = asset.create(api=self.sdk_api)
            self.assertTrue(created_ok)
            self.assertTrue(asset._id)

        with self.app.test_request_context():
            # Check the asset in MongoDB
            resp = self.get(url_for('nodes|item_lookup', _id=asset._id), auth_token='token')
            db_asset = resp.json()
            self.assertEqual('Test asset', db_asset['name'])

        return asset

    def test_delete_asset(self):
        asset = self.test_create_asset()
        with self.app.test_request_context():
            asset.delete(api=self.sdk_api)

    def test_upload_file_to_project(self):
        with self.app.test_request_context():
            resp = pillarsdk.File.upload_to_project(
                self.project_id,
                'image/png',
                blender_desktop_logo_path,
                api=self.sdk_api
            )
            file_id = resp['file_id']
            self.assertTrue(file_id)

        # Check the file in MongoDB
        with self.app.test_request_context():
            resp = self.get(url_for('files|item_lookup', _id=file_id), auth_token='token')
            file_doc = resp.json()
            self.assertEqual('BlenderDesktopLogo.png', file_doc['filename'])

    def test_create_asset_from_file(self):
        # Create a group node to serve as parent.
        with self.app.test_request_context():
            resp = self.post(url_for('nodes|resource'), auth_token='token',
                             json={
                                 'name': 'Group node',
                                 'node_type': 'group',
                                 'project': self.project_id,
                                 'properties': {}
                             },
                             expected_status=201)
            parent_id = resp.json()['_id']

        with self.app.test_request_context(), open(blender_desktop_logo_path, 'rb') as fileobj:
            resp = pillarsdk.Node.create_asset_from_file(
                unicode(self.project_id),
                unicode(parent_id),
                'image',
                blender_desktop_logo_path,
                mimetype='image/jpeg',
                always_create_new_node=False,
                fileobj=fileobj,
                api=self.sdk_api)

            node_id = resp._id
            self.assertTrue(node_id)

        # Check the node in MongoDB
        with self.app.test_request_context():
            resp = self.get(url_for('nodes|item_lookup', _id=node_id), auth_token='token')
            node_doc = resp.json()
            self.assertEqual('BlenderDesktopLogo.png', node_doc['name'])
