# -*- encoding: utf-8 -*-

import json
import copy
import sys
import logging
import datetime
import os
import base64

from bson import ObjectId, tz_util

# Override Eve settings before importing eve.tests.
import common_test_settings

common_test_settings.override_eve()

from eve.tests import TestMinimal
import pymongo.collection
from flask.testing import FlaskClient
import responses

from common_test_data import EXAMPLE_PROJECT, EXAMPLE_FILE

MY_PATH = os.path.dirname(os.path.abspath(__file__))

TEST_EMAIL_USER = 'koro'
TEST_EMAIL_ADDRESS = '%s@testing.blender.org' % TEST_EMAIL_USER
TEST_FULL_NAME = u'врач Сергей'
TEST_SUBCLIENT_TOKEN = 'my-subclient-token-for-pillar'
BLENDER_ID_TEST_USERID = 1896
BLENDER_ID_USER_RESPONSE = {'status': 'success',
                            'user': {'email': TEST_EMAIL_ADDRESS,
                                     'full_name': TEST_FULL_NAME,
                                     'id': BLENDER_ID_TEST_USERID},
                            'token_expires': 'Mon, 1 Jan 2018 01:02:03 GMT'}

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

        logging.getLogger('').setLevel(logging.DEBUG)
        logging.getLogger('application').setLevel(logging.DEBUG)
        logging.getLogger('werkzeug').setLevel(logging.DEBUG)
        logging.getLogger('eve').setLevel(logging.DEBUG)

        from eve.utils import config
        config.DEBUG = True

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

    def create_user(self, user_id='cafef00dc379cf10c4aaceaf', roles=('subscriber', )):
        with self.app.test_request_context():
            users = self.app.data.driver.db['users']
            assert isinstance(users, pymongo.collection.Collection)

            result = users.insert_one({
                '_id': ObjectId(user_id),
                '_updated': datetime.datetime(2016, 4, 15, 13, 15, 11, tzinfo=tz_util.utc),
                '_created': datetime.datetime(2016, 4, 15, 13, 15, 11, tzinfo=tz_util.utc),
                'username': 'tester',
                'groups': [],
                'roles': list(roles),
                'settings': {'email_communications': 1},
                'auth': [{'token': '',
                          'user_id': unicode(BLENDER_ID_TEST_USERID),
                          'provider': 'blender-id'}],
                'full_name': u'คนรักของผัดไทย',
                'email': TEST_EMAIL_ADDRESS
            })

            return result.inserted_id

    def create_valid_auth_token(self, user_id, token='token'):
        now = datetime.datetime.now(tz_util.utc)
        future = now + datetime.timedelta(days=1)

        with self.app.test_request_context():
            from application.utils import authentication as auth

            token_data = auth.store_token(user_id, token, future, None)

        return token_data

    def mock_blenderid_validate_unhappy(self):
        """Sets up Responses to mock unhappy validation flow."""

        responses.add(responses.POST,
                      '%s/u/validate_token' % self.app.config['BLENDER_ID_ENDPOINT'],
                      json={'status': 'fail'},
                      status=403)

    def mock_blenderid_validate_happy(self):
        """Sets up Responses to mock happy validation flow."""

        responses.add(responses.POST,
                      '%s/u/validate_token' % self.app.config['BLENDER_ID_ENDPOINT'],
                      json=BLENDER_ID_USER_RESPONSE,
                      status=200)

    def make_header(self, username, subclient_id=''):
        """Returns a Basic HTTP Authentication header value."""

        return 'basic ' + base64.b64encode('%s:%s' % (username, subclient_id))
