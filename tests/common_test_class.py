import json
import copy
import sys
import logging
import os
import base64

from bson import ObjectId
from eve.tests import TestMinimal
import pymongo.collection
from flask.testing import FlaskClient
import httpretty

from common_test_data import EXAMPLE_PROJECT, EXAMPLE_FILE

MY_PATH = os.path.dirname(os.path.abspath(__file__))

TEST_EMAIL_USER = 'koro'
TEST_EMAIL_ADDRESS = '%s@testing.blender.org' % TEST_EMAIL_USER

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)-15s %(levelname)8s %(name)s %(message)s')


class AbstractPillarTest(TestMinimal):
    def setUp(self, **kwargs):
        eve_settings_file = os.path.join(MY_PATH, 'common_test_settings.py')
        pillar_config_file = os.path.join(MY_PATH, 'config_testing.py')
        kwargs['settings_file'] = eve_settings_file
        os.environ['EVE_SETTINGS'] = eve_settings_file
        os.environ['PILLAR_CONFIG'] = pillar_config_file
        super(AbstractPillarTest, self).setUp(**kwargs)

        from application import app

        logging.getLogger('application').setLevel(logging.DEBUG)
        logging.getLogger('werkzeug').setLevel(logging.DEBUG)
        logging.getLogger('eve').setLevel(logging.DEBUG)

        self.app = app
        self.client = app.test_client()
        assert isinstance(self.client, FlaskClient)

    def tearDown(self):
        super(AbstractPillarTest, self).tearDown()

        # Not only delete self.app (like the superclass does),
        # but also un-import the application.
        del sys.modules['application']

    def ensure_file_exists(self, file_overrides=None):
        self.ensure_project_exists()
        with self.app.test_request_context():
            files_collection = self.app.data.driver.db['files']
            assert isinstance(files_collection, pymongo.collection.Collection)

            file = copy.deepcopy(EXAMPLE_FILE)
            if file_overrides is not None:
                file.update(file_overrides)

            result = files_collection.insert_one(file)
            file_id = result.inserted_id

            # Re-fetch from the database, so that we're sure we return the same as is stored.
            # This is necessary as datetimes are rounded by MongoDB.
            from_db = files_collection.find_one(file_id)
            return file_id, from_db

    def ensure_project_exists(self, project_overrides=None):
        with self.app.test_request_context():
            projects_collection = self.app.data.driver.db['projects']
            assert isinstance(projects_collection, pymongo.collection.Collection)

            project = copy.deepcopy(EXAMPLE_PROJECT)
            if project_overrides is not None:
                project.update(project_overrides)

            found = projects_collection.find_one(project['_id'])
            if found is None:
                result = projects_collection.insert_one(project)
                return result.inserted_id, project

            return found['_id'], found

    def htp_blenderid_validate_unhappy(self):
        """Sets up HTTPretty to mock unhappy validation flow."""

        httpretty.register_uri(httpretty.POST,
                               '%s/u/validate_token' % self.app.config['BLENDER_ID_ENDPOINT'],
                               body=json.dumps(
                                   {'data': {'token': 'Token is invalid'}, 'status': 'fail'}),
                               content_type="application/json")

    def htp_blenderid_validate_happy(self):
        """Sets up HTTPretty to mock happy validation flow."""

        httpretty.register_uri(httpretty.POST,
                               '%s/u/validate_token' % self.app.config['BLENDER_ID_ENDPOINT'],
                               body=json.dumps(
                                   {'data': {'user': {'email': TEST_EMAIL_ADDRESS, 'id': 5123}},
                                    'status': 'success'}),
                               content_type="application/json")

    def make_header(self, username, password=''):
        """Returns a Basic HTTP Authentication header value."""

        return 'basic ' + base64.b64encode('%s:%s' % (username, password))
