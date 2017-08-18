# -*- encoding: utf-8 -*-

import base64
import copy
import datetime
import json
import logging
import os
import sys
import typing
import unittest.mock

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib.parse import urlencode

from bson import ObjectId, tz_util

# Override Eve settings before importing eve.tests.
from pillar.tests import eve_test_settings

eve_test_settings.override_eve()

from eve.tests import TestMinimal
import pymongo.collection
from flask.testing import FlaskClient
import flask.ctx
import responses

import pillar
from . import common_test_data as ctd

MY_PATH = os.path.dirname(os.path.abspath(__file__))

TEST_EMAIL_USER = 'koro'
TEST_EMAIL_ADDRESS = '%s@testing.blender.org' % TEST_EMAIL_USER
TEST_FULL_NAME = 'врач Сергей'
TEST_SUBCLIENT_TOKEN = 'my-subclient-token-for-pillar'
BLENDER_ID_USER_RESPONSE = {'status': 'success',
                            'user': {'email': TEST_EMAIL_ADDRESS,
                                     'full_name': TEST_FULL_NAME,
                                     'id': ctd.BLENDER_ID_TEST_USERID},
                            'token_expires': 'Mon, 1 Jan 2018 01:02:03 GMT'}


class PillarTestServer(pillar.PillarServer):
    def _load_flask_config(self):
        super(PillarTestServer, self)._load_flask_config()

        pillar_config_file = os.path.join(MY_PATH, 'config_testing.py')
        self.config.from_pyfile(pillar_config_file)

    def _config_logging(self):
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)-15s %(levelname)8s %(name)s %(message)s')
        logging.getLogger('').setLevel(logging.DEBUG)
        logging.getLogger('pillar').setLevel(logging.DEBUG)
        logging.getLogger('werkzeug').setLevel(logging.DEBUG)
        logging.getLogger('eve').setLevel(logging.DEBUG)

    def _config_celery(self):
        """Disables Celery by entirely mocking it.

        Without this, actual Celery tasks will be created while the tests are running.
        """

        from celery import Celery

        self.celery = unittest.mock.MagicMock(Celery)

        def fake_task(*task_args, **task_kwargs):
            def decorator(f):
                def delay(*args, **kwargs):
                    return f(*args, **kwargs)

                f.delay = delay
                f.si = unittest.mock.MagicMock()
                f.s = unittest.mock.MagicMock()
                return f

            return decorator

        self.celery.task = fake_task


class AbstractPillarTest(TestMinimal):
    pillar_server_class = PillarTestServer

    @classmethod
    def setUpClass(cls):
        import tempfile

        # Store the global temporary directory location, as Pillar itself will
        # change this into the config['STORAGE_DIR'] directory. If we don't
        # restore that, mkdtemp() will keep trying to create inside its previously
        # created temporary storage directory.
        cls._orig_tempdir = tempfile.gettempdir()

        # Point the storage directory to something temporary.
        try:
            cls._pillar_storage_dir = tempfile.mkdtemp(prefix='test-pillar-storage-')
        except FileNotFoundError as ex:
            raise FileNotFoundError(f'Error creating temp dir: {ex}')
        os.environ['PILLAR_STORAGE_DIR'] = cls._pillar_storage_dir

    @classmethod
    def tearDownClass(cls):
        import tempfile
        import shutil

        tempfile.tempdir = cls._orig_tempdir
        shutil.rmtree(cls._pillar_storage_dir)

    def setUp(self, **kwargs):
        eve_settings_file = os.path.join(MY_PATH, 'eve_test_settings.py')
        kwargs['settings_file'] = eve_settings_file
        os.environ['EVE_SETTINGS'] = eve_settings_file
        super(AbstractPillarTest, self).setUp(**kwargs)

        from eve.utils import config
        config.DEBUG = True

        self.app = self.pillar_server_class(os.path.dirname(os.path.dirname(__file__)))
        self.assertEqual(self.app.config['STORAGE_DIR'], self._pillar_storage_dir)

        # Run self.enter_app_context() to create this context.
        self._app_ctx: flask.ctx.AppContext = None

        self.app.process_extensions()
        assert self.app.config['MONGO_DBNAME'] == 'pillar_test'

        self.client = self.app.test_client()
        assert isinstance(self.client, FlaskClient)

    def tearDown(self):
        super(AbstractPillarTest, self).tearDown()

        if self._app_ctx is not None:
            self._app_ctx.__exit__(*sys.exc_info())

        # Not only delete self.app (like the superclass does),
        # but also un-import the application.
        self.unload_modules('pillar')

    def enter_app_context(self):
        """Globally starts an app context.

        The app context is automatically exited upon testcase teardown.
        """

        self._app_ctx: flask.ctx.AppContext = self.app.app_context()
        self._app_ctx.__enter__()

    def unload_modules(self, module_name):
        """Uploads the named module, and all submodules."""

        del sys.modules[module_name]

        remove = {modname for modname in sys.modules
                  if modname.startswith('%s.' % module_name)}
        for modname in remove:
            del sys.modules[modname]

    def ensure_file_exists(self, file_overrides=None):
        if file_overrides and file_overrides.get('project'):
            self.ensure_project_exists({'_id': file_overrides['project']})
        else:
            self.ensure_project_exists()

        with self.app.test_request_context():
            files_collection = self.app.data.driver.db['files']
            assert isinstance(files_collection, pymongo.collection.Collection)

            file = copy.deepcopy(ctd.EXAMPLE_FILE)
            if file_overrides is not None:
                file.update(file_overrides)
            if '_id' in file and file['_id'] is None:
                del file['_id']

            result = files_collection.insert_one(file)
            file_id = result.inserted_id

            # Re-fetch from the database, so that we're sure we return the same as is stored.
            # This is necessary as datetimes are rounded by MongoDB.
            from_db = files_collection.find_one(file_id)
            return file_id, from_db

    def ensure_project_exists(self, project_overrides=None) -> typing.Tuple[ObjectId, dict]:
        self.ensure_group_exists(ctd.EXAMPLE_ADMIN_GROUP_ID, 'project admin')
        self.ensure_group_exists(ctd.EXAMPLE_PROJECT_READONLY_GROUP_ID, 'r/o group')
        self.ensure_group_exists(ctd.EXAMPLE_PROJECT_READONLY_GROUP2_ID, 'r/o group 2')
        self.ensure_user_exists(ctd.EXAMPLE_PROJECT_OWNER_ID,
                                'proj-owner',
                                [ctd.EXAMPLE_ADMIN_GROUP_ID])

        with self.app.test_request_context():
            projects_collection = self.app.data.driver.db['projects']
            assert isinstance(projects_collection, pymongo.collection.Collection)

            project = copy.deepcopy(ctd.EXAMPLE_PROJECT)
            if project_overrides is not None:
                for key, value in project_overrides.items():
                    if value is None:
                        project.pop(key, None)
                    else:
                        project[key] = value

            found = projects_collection.find_one(project['_id'])
            if found is None:
                result = projects_collection.insert_one(project)
                return result.inserted_id, project

            return found['_id'], found

    def ensure_user_exists(self, user_id, name, group_ids=()):
        user = copy.deepcopy(ctd.EXAMPLE_USER)
        user['groups'] = list(group_ids)
        user['full_name'] = name
        user['_id'] = ObjectId(user_id)

        with self.app.test_request_context():
            users_coll = self.app.data.driver.db['users']
            assert isinstance(users_coll, pymongo.collection.Collection)

            found = users_coll.find_one(user_id)
            if found:
                return

            result = users_coll.insert_one(user)
            assert result.inserted_id

    def ensure_group_exists(self, group_id, name):
        group_id = ObjectId(group_id)

        with self.app.test_request_context():
            groups_coll = self.app.data.driver.db['groups']
            assert isinstance(groups_coll, pymongo.collection.Collection)

            found = groups_coll.find_one(group_id)
            if found:
                return group_id

            result = groups_coll.insert_one({'_id': group_id, 'name': name})
            assert result.inserted_id
            return result.inserted_id

    def create_user(self, user_id='cafef00dc379cf10c4aaceaf', roles=('subscriber',),
                    groups=None, *, token: str = None, email: str = TEST_EMAIL_ADDRESS):
        from pillar.api.utils.authentication import make_unique_username
        import uuid

        with self.app.test_request_context():
            users = self.app.data.driver.db['users']
            assert isinstance(users, pymongo.collection.Collection)

            result = users.insert_one({
                '_id': ObjectId(user_id),
                '_updated': datetime.datetime(2016, 4, 15, 13, 15, 11, tzinfo=tz_util.utc),
                '_created': datetime.datetime(2016, 4, 15, 13, 15, 11, tzinfo=tz_util.utc),
                '_etag': 'unittest-%s' % uuid.uuid4().hex,
                'username': make_unique_username('tester'),
                'groups': groups or [],
                'roles': list(roles),
                'settings': {'email_communications': 1},
                'auth': [{'token': '',
                          'user_id': str(ctd.BLENDER_ID_TEST_USERID),
                          'provider': 'blender-id'}],
                'full_name': 'คนรักของผัดไทย',
                'email': email
            })

            user_id = result.inserted_id

        if token:
            self.create_valid_auth_token(user_id, token)

        return user_id

    def create_user_object(self, user_id=ObjectId(), roles=frozenset(), group_ids=None):
        """Creates a pillar.auth.UserClass object.

        :rtype: pillar.auth.UserClass
        """

        from pillar.auth import UserClass

        db_user = copy.deepcopy(ctd.EXAMPLE_USER)
        db_user['_id'] = user_id
        db_user['roles'] = list(roles) if roles is not None else None

        if group_ids is not None:
            db_user['groups'] = list(group_ids)

        return UserClass.construct('', db_user)

    def login_api_as(self, user_id=ObjectId(), roles=frozenset(), group_ids=None):
        """Creates a pillar.auth.UserClass object and sets it as g.current_user

        Requires an active request context!

        :rtype: pillar.auth.UserClass
        """

        from flask import g

        user = self.create_user_object(user_id, roles, group_ids)
        g.current_user = user

        return user

    def create_valid_auth_token(self, user_id, token='token'):
        now = datetime.datetime.now(tz_util.utc)
        future = now + datetime.timedelta(days=1)

        with self.app.test_request_context():
            from pillar.api.utils import authentication as auth

            token_data = auth.store_token(user_id, token, future, None)

        return token_data

    def create_project_with_admin(self, user_id='cafef00dc379cf10c4aaceaf', roles=('subscriber',),
                                  project_overrides=None):
        """Creates a project and a user that's member of the project's admin group.

        :returns: (project_id, user_id)
        :rtype: tuple
        """
        project_id, proj = self.ensure_project_exists(project_overrides=project_overrides)
        user_id = self.create_project_admin(proj, user_id, roles)

        return project_id, user_id

    def create_project_admin(self, proj, user_id='cafef00dc379cf10c4aaceaf', roles=('subscriber',)):
        """Creates a user that's member of the project's admin group.

        :param proj: project document, or at least a dict with permissions in it.
        :type proj: dict
        :returns: user_id
        :rtype: ObjectId
        """

        admin_group_id = proj['permissions']['groups'][0]['group']
        user_id = self.create_user(user_id=user_id, roles=roles, groups=[admin_group_id])

        return user_id

    def create_node(self, node_doc):
        """Creates a node, returning its ObjectId. """

        with self.app.test_request_context():
            nodes_coll = self.app.data.driver.db['nodes']
            result = nodes_coll.insert_one(node_doc)
        return result.inserted_id

    def badger(self, user_email, roles, action, srv_token=None):
        """Creates a service account, and uses it to grant or revoke a role to the user.

        To skip creation of the service account, pass a srv_token.

        :returns: the authentication token of the created service account.
        :rtype: str
        """

        if isinstance(roles, str):
            roles = {roles}

        # Create a service account if needed.
        if srv_token is None:
            from pillar.api.service import create_service_account
            with self.app.test_request_context():
                _, srv_token_doc = create_service_account('service@example.com',
                                                          {'badger'},
                                                          {'badger': list(roles)})
                srv_token = srv_token_doc['token']

        for role in roles:
            self.post('/api/service/badger',
                      auth_token=srv_token,
                      json={'action': action,
                            'role': role,
                            'user_email': user_email},
                      expected_status=204)
        return srv_token

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

    def make_header(self, username: str, subclient_id: str = '') -> bytes:
        """Returns a Basic HTTP Authentication header value."""

        content = '%s:%s' % (username, subclient_id)
        return b'basic ' + base64.b64encode(content.encode())

    def create_standard_groups(self, additional_groups=()) -> dict:
        """Creates standard admin/demo/subscriber groups, plus any additional.

        :returns: mapping from group name to group ID
        """
        from pillar.api import service

        with self.app.test_request_context():
            group_ids = {}
            groups_coll = self.app.data.driver.db['groups']

            for group_name in ['admin', 'demo', 'subscriber'] + list(additional_groups):
                result = groups_coll.insert_one({'name': group_name})
                group_ids[group_name] = result.inserted_id

            service.fetch_role_to_group_id_map()

        return group_ids

    def fetch_project_from_db(self, project_id=ctd.EXAMPLE_PROJECT_ID):
        with self.app.app_context():
            proj_coll = self.app.db()['projects']
            return proj_coll.find_one(project_id)

    def fetch_user_from_db(self, user_id=ctd.EXAMPLE_USER['_id']):
        with self.app.app_context():
            users_coll = self.app.db('users')
            return users_coll.find_one(user_id)

    @staticmethod
    def join_url_params(params):
        """Constructs a query string from a dictionary and appends it to a url.

        Usage::

            >>> AbstractPillarTest.join_url_params("pillar:5000/shots",
                    {"page-id": 2, "NodeType": "Shot Group"})
            'pillar:5000/shots?page-id=2&NodeType=Shot+Group'
        """

        if params is None:
            return None

        if not isinstance(params, dict):
            return params

        def convert_to_bytes(param):
            if isinstance(param, dict):
                return json.dumps(param, sort_keys=True)
            if isinstance(param, str):
                return param.encode('utf-8')
            return param

        # Pass as (key, value) pairs, so that the sorted order is maintained.
        jsonified_params = [
            (key, convert_to_bytes(params[key]))
            for key in sorted(params.keys())]
        return urlencode(jsonified_params)

    def client_request(self, method, path, qs=None, expected_status=200, auth_token=None, json=None,
                       data=None, headers=None, files=None, content_type=None, etag=None):
        """Performs a HTTP request to the server."""

        from pillar.api.utils import dumps
        import json as mod_json

        headers = headers or {}
        if auth_token is not None:
            headers['Authorization'] = self.make_header(auth_token)

        if json is not None:
            data = dumps(json)
            headers['Content-Type'] = 'application/json'

        if etag is not None:
            if method in {'PUT', 'PATCH', 'DELETE'}:
                headers['If-Match'] = etag
            elif method == 'GET':
                headers['If-None-Match'] = etag
            else:
                raise ValueError('Not sure what to do with etag and method %s' % method)

        if files:
            data = data or {}
            content_type = 'multipart/form-data'
            data.update(files)

        resp = self.client.open(path=path, method=method, data=data, headers=headers,
                                content_type=content_type,
                                query_string=self.join_url_params(qs))
        self.assertEqual(expected_status, resp.status_code,
                         'Expected status %i but got %i. Response: %s' % (
                             expected_status, resp.status_code, resp.data
                         ))

        def get_json():
            if resp.mimetype != 'application/json':
                raise TypeError('Unable to load JSON from mimetype %r' % resp.mimetype)
            return mod_json.loads(resp.data)

        resp.json = get_json
        resp.get_json = get_json

        return resp

    def get(self, *args, **kwargs):
        return self.client_request('GET', *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.client_request('POST', *args, **kwargs)

    def put(self, *args, **kwargs):
        return self.client_request('PUT', *args, **kwargs)

    def delete(self, *args, **kwargs):
        return self.client_request('DELETE', *args, **kwargs)

    def patch(self, *args, **kwargs):
        return self.client_request('PATCH', *args, **kwargs)

    def assertAllowsAccess(self,
                           token: typing.Union[str, dict],
                           expected_user_id: typing.Union[str, ObjectId] = None):
        """Asserts that this authentication token allows access to /api/users/me."""

        if isinstance(token, dict) and 'token' in token:
            token = token['token']

        if not isinstance(token, str):
            raise TypeError(f'token should be a string, but is {token!r}')
        if expected_user_id and not isinstance(expected_user_id, (str, ObjectId)):
            raise TypeError('expected_user_id should be a string or ObjectId, '
                            f'but is {expected_user_id!r}')

        resp = self.get('/api/users/me', expected_status=200, auth_token=token).json()

        if expected_user_id:
            self.assertEqual(resp['_id'], str(expected_user_id))


def mongo_to_sdk(data):
    """Transforms a MongoDB dict to a dict suitable to give to the PillarSDK.

    Not efficient, as it converts to JSON and back again. Only use in unittests.
    """

    import pillar.api.utils
    import json

    as_json = pillar.api.utils.dumps(data)
    return json.loads(as_json)
