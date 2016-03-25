import json
import copy
import sys
import logging
import os

from eve.tests import TestMinimal
import pymongo.collection
from flask.testing import FlaskClient
import httpretty

from test_data import EXAMPLE_PROJECT, EXAMPLE_FILE

BLENDER_ID_ENDPOINT = 'http://127.0.0.1:8001'  # nonexistant server, no trailing slash!
MY_PATH = os.path.dirname(os.path.abspath(__file__))

TEST_EMAIL_USER = 'koro'
TEST_EMAIL_ADDRESS = '%s@testing.blender.org' % TEST_EMAIL_USER

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)-15s %(levelname)8s %(name)s %(message)s')


class AbstractPillarTest(TestMinimal):
    def setUp(self, **kwargs):
        settings_file = os.path.join(MY_PATH, 'test_settings.py')
        kwargs['settings_file'] = settings_file
        os.environ['EVE_SETTINGS'] = settings_file
        super(AbstractPillarTest, self).setUp(**kwargs)

        from application import app

        app.config['BLENDER_ID_ENDPOINT'] = BLENDER_ID_ENDPOINT
        logging.getLogger('application').setLevel(logging.DEBUG)
        logging.getLogger('werkzeug').setLevel(logging.DEBUG)

        self.app = app
        self.client = app.test_client()
        assert isinstance(self.client, FlaskClient)

    def tearDown(self):
        super(AbstractPillarTest, self).tearDown()

        # Not only delete self.app (like the superclass does),
        # but also un-import the application.
        del sys.modules['application']

    def _ensure_file_exists(self, file_overrides=None):
        with self.app.test_request_context():
            files_collection = self.app.data.driver.db['files']
            projects_collection = self.app.data.driver.db['projects']
            assert isinstance(files_collection, pymongo.collection.Collection)

            file = copy.deepcopy(EXAMPLE_FILE)
            if file_overrides is not None:
                file.update(file_overrides)

            projects_collection.insert_one(EXAMPLE_PROJECT)
            result = files_collection.insert_one(file)
            file_id = result.inserted_id
        return file_id, EXAMPLE_FILE

    def htp_blenderid_validate_unhappy(self):
        """Sets up HTTPretty to mock unhappy validation flow."""

        httpretty.register_uri(httpretty.POST,
                               '%s/u/validate_token' % BLENDER_ID_ENDPOINT,
                               body=json.dumps(
                                   {'data': {'token': 'Token is invalid'}, 'status': 'fail'}),
                               content_type="application/json")

    def htp_blenderid_validate_happy(self):
        """Sets up HTTPretty to mock happy validation flow."""

        httpretty.register_uri(httpretty.POST,
                               '%s/u/validate_token' % BLENDER_ID_ENDPOINT,
                               body=json.dumps(
                                   {'data': {'user': {'email': TEST_EMAIL_ADDRESS, 'id': 5123}},
                                    'status': 'success'}),
                               content_type="application/json")

