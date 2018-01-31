"""Unit tests for creating and editing projects_blueprint."""

import datetime
import functools
import json
import logging
import urllib.request, urllib.parse, urllib.error

from bson import ObjectId
import bson.tz_util
from pymongo.collection import ReturnDocument

from pillar.tests import AbstractPillarTest

log = logging.getLogger(__name__)


class AbstractProjectTest(AbstractPillarTest):
    def _create_user_with_token(self, roles, token, user_id='cafef00df00df00df00df00d'):
        user_id = self.create_user(roles=roles, user_id=user_id)
        self.create_valid_auth_token(user_id, token)
        return user_id

    def _create_project(self, project_name, token):
        resp = self.client.post('/api/p/create',
                                headers={'Authorization': self.make_header(token)},
                                data={'project_name': project_name})
        return resp

    def _create_user_and_project(self, roles, user_id='cafef00df00df00df00df00d', token='token',
                                 project_name='Prøject El Niño'):
        self._create_user_with_token(roles, token, user_id=user_id)
        resp = self._create_project(project_name, token)

        self.assertEqual(201, resp.status_code, resp.data)
        project = json.loads(resp.data)

        return project


class ProjectCreationTest(AbstractProjectTest):
    def test_project_creation_wrong_role(self):
        self._create_user_with_token(['whatever'], 'token')
        resp = self._create_project('Prøject El Niño', 'token')

        self.assertEqual(403, resp.status_code)

        # Test that the project wasn't created.
        with self.app.test_request_context():
            projects = self.app.data.driver.db['projects']
            self.assertEqual(0, len(list(projects.find())))

    def test_project_creation_good_role(self):
        user_id = self._create_user_with_token(['subscriber'], 'token')
        resp = self._create_project('Prøject El Niño', 'token')
        self.assertEqual(201, resp.status_code)

        # The response of a POST is the entire project, but we'll test a GET on
        # the returned Location nevertheless.
        project_info = json.loads(resp.data.decode('utf-8'))
        project_id = project_info['_id']

        # Test that the Location header contains the location of the project document.
        self.assertEqual('http://localhost/api/projects/%s' % project_id,
                         resp.headers['Location'])

        # GET the project from the URL in the Location header to see if that works too.
        auth_header = {'Authorization': self.make_header('token')}
        resp = self.client.get(resp.headers['Location'], headers=auth_header)
        project = json.loads(resp.data.decode('utf-8'))
        project_id = project['_id']

        # Check some of the more complex/interesting fields.
        self.assertEqual('Prøject El Niño', project['name'])
        self.assertEqual(str(user_id), project['user'])
        self.assertEqual('p-%s' % project_id, project['url'])
        self.assertEqual(1, len(project['permissions']['groups']))

        # Check the etag
        resp = self.client.get('/api/projects/%s' % project_id, headers=auth_header)
        from_db = json.loads(resp.data)
        self.assertEqual(from_db['_etag'], project['_etag'])

        group_id = ObjectId(project['permissions']['groups'][0]['group'])

        # Check that there is a group for the project, and that the user is member of it.
        with self.app.test_request_context():
            groups = self.app.data.driver.db['groups']
            users = self.app.data.driver.db['users']

            group = groups.find_one(group_id)
            db_user = users.find_one(user_id)

            self.assertEqual(str(project_id), group['name'])
            self.assertIn(group_id, db_user['groups'])

    def test_project_creation_access_admin(self):
        """Admin-created projects should be public"""

        proj = self._create_user_and_project(roles={'admin', 'demo'})
        self.assertEqual(['GET'], proj['permissions']['world'])

    def test_project_creation_access_subscriber(self):
        """Subscriber-created projects should be private"""

        proj = self._create_user_and_project(roles={'subscriber'})
        self.assertEqual([], proj['permissions']['world'])
        self.assertTrue(proj['is_private'])

        # Also check the database contents
        with self.app.test_request_context():
            project_id = ObjectId(proj['_id'])
            db_proj = self.app.data.driver.db['projects'].find_one(project_id)
            self.assertEqual([], db_proj['permissions']['world'])
            self.assertTrue(db_proj['is_private'])

    def test_project_list(self):
        """Test that we get an empty list when querying for non-existing projects, instead of 403"""

        proj_a = self._create_user_and_project(user_id=24 * 'a',
                                               roles={'subscriber'},
                                               project_name='Prøject A',
                                               token='token-a')
        proj_b = self._create_user_and_project(user_id=24 * 'b',
                                               roles={'subscriber'},
                                               project_name='Prøject B',
                                               token='token-b')

        # Assertion: each user must have access to their own project.
        resp = self.client.get('/api/projects/%s' % proj_a['_id'],
                               headers={'Authorization': self.make_header('token-a')})
        self.assertEqual(200, resp.status_code, resp.data)
        resp = self.client.get('/api/projects/%s' % proj_b['_id'],
                               headers={'Authorization': self.make_header('token-b')})
        self.assertEqual(200, resp.status_code, resp.data)

        # Getting a project list should return projects you have access to.
        resp = self.client.get('/api/projects',
                               headers={'Authorization': self.make_header('token-a')})
        self.assertEqual(200, resp.status_code)
        proj_list = json.loads(resp.data)
        self.assertEqual({'Prøject A'}, {p['name'] for p in proj_list['_items']})

        resp = self.client.get('/api/projects',
                               headers={'Authorization': self.make_header('token-b')})
        self.assertEqual(200, resp.status_code)
        proj_list = json.loads(resp.data)
        self.assertEqual({'Prøject B'}, {p['name'] for p in proj_list['_items']})

        # No access to anything for user C, should result in empty list.
        self._create_user_with_token(roles={'subscriber'}, token='token-c', user_id=24 * 'c')
        resp = self.client.get('/api/projects',
                               headers={'Authorization': self.make_header('token-c')})
        self.assertEqual(200, resp.status_code)
        proj_list = json.loads(resp.data)
        self.assertEqual([], proj_list['_items'])


class ProjectEditTest(AbstractProjectTest):
    def test_editing_as_subscriber(self):
        """Test that we can set certain fields, but not all."""

        from pillar.api.utils import remove_private_keys, PillarJSONEncoder
        dumps = functools.partial(json.dumps, cls=PillarJSONEncoder)

        project_info = self._create_user_and_project(['subscriber'])
        project_url = '/api/projects/%(_id)s' % project_info

        project = self.get(project_url, auth_token='token').json()

        # Create another user we can try and assign the project to.
        other_user_id = 'f00dd00df00dd00df00dd00d'
        self._create_user_with_token(['subscriber'], 'other-token', user_id=other_user_id)

        # Unauthenticated should be forbidden
        self.put('/api/projects/%s' % project['_id'],
                 json=remove_private_keys(project),
                 etag=project['_etag'],
                 expected_status=403)

        # Regular user should be able to PUT, but only be able to edit certain fields.
        put_project = remove_private_keys(project)
        put_project['url'] = 'very-offensive-url'
        put_project['description'] = 'Blender je besplatan set alata za izradu interaktivnog 3D ' \
                                     'sadržaja pod različitim operativnim sustavima.'
        put_project['name'] = 'โครงการปั่นเมฆ'
        put_project['summary'] = 'Это переведена на Google'
        put_project['status'] = 'pending'
        put_project['category'] = 'software'
        put_project['user'] = other_user_id

        # Try making the project public. This should update is_private as well.
        put_project['permissions']['world'] = ['GET']
        self.put(project_url,
                 json=put_project,
                 auth_token='token',
                 etag=project['_etag'])

        # Re-fetch from database to see which fields actually made it there.
        # equal to put_project -> changed in DB
        # equal to project -> not changed in DB
        db_proj = self.get(project_url, auth_token='token').json()
        self.assertEqual(project['url'], db_proj['url'])
        self.assertEqual(put_project['description'], db_proj['description'])
        self.assertEqual(put_project['name'], db_proj['name'])
        self.assertEqual(put_project['summary'], db_proj['summary'])
        self.assertEqual(project['status'], db_proj['status'])
        self.assertEqual(project['category'], db_proj['category'])

        # Project should be consistent.
        self.assertEqual(False, db_proj['is_private'])
        self.assertEqual(['GET'], db_proj['permissions']['world'])

    def test_editing_as_admin(self):
        """Test that we can set all fields as admin."""

        from pillar.api.utils import remove_private_keys, PillarJSONEncoder
        dumps = functools.partial(json.dumps, cls=PillarJSONEncoder)

        project_info = self._create_user_and_project(['subscriber', 'admin'])
        project_url = '/api/projects/%(_id)s' % project_info

        resp = self.client.get(project_url)
        project = json.loads(resp.data.decode('utf-8'))

        # Create another user we can try and assign the project to.
        other_user_id = 'f00dd00df00dd00df00dd00d'
        self._create_user_with_token(['subscriber'], 'other-token', user_id=other_user_id)

        # Admin user should be able to PUT everything.
        put_project = remove_private_keys(project)
        put_project['url'] = 'very-offensive-url'
        put_project['description'] = 'Blender je besplatan set alata za izradu interaktivnog 3D ' \
                                     'sadržaja pod različitim operativnim sustavima.'
        put_project['name'] = 'โครงการปั่นเมฆ'
        put_project['summary'] = 'Это переведена на Google'
        put_project['is_private'] = False
        put_project['status'] = 'pending'
        put_project['category'] = 'software'
        put_project['user'] = other_user_id

        resp = self.client.put(project_url,
                               data=dumps(put_project),
                               headers={'Authorization': self.make_header('token'),
                                        'Content-Type': 'application/json',
                                        'If-Match': project['_etag']})
        self.assertEqual(200, resp.status_code, resp.data)

        # Re-fetch from database to see which fields actually made it there.
        # equal to put_project -> changed in DB
        # equal to project -> not changed in DB
        resp = self.client.get('/api/projects/%s' % project['_id'])
        db_proj = json.loads(resp.data)
        self.assertEqual(put_project['url'], db_proj['url'])
        self.assertEqual(put_project['description'], db_proj['description'])
        self.assertEqual(put_project['name'], db_proj['name'])
        self.assertEqual(put_project['summary'], db_proj['summary'])
        self.assertEqual(put_project['is_private'], db_proj['is_private'])
        self.assertEqual(put_project['status'], db_proj['status'])
        self.assertEqual(put_project['category'], db_proj['category'])
        self.assertEqual(put_project['user'], db_proj['user'])

    def test_edits_by_nonowner_admin(self):
        """Any admin should be able to edit any project."""

        from pillar.api.utils import remove_private_keys, PillarJSONEncoder
        dumps = functools.partial(json.dumps, cls=PillarJSONEncoder)

        # Create test project.
        project = self._create_user_and_project(['subscriber'])
        project_id = project['_id']
        project_url = '/api/projects/%s' % project_id

        # Create test user.
        self._create_user_with_token(['admin'], 'admin-token', user_id='cafef00dbeefcafef00dbeef')

        # Admin user should be able to PUT.
        put_project = remove_private_keys(project)
        put_project['name'] = 'โครงการปั่นเมฆ'

        resp = self.client.put(project_url,
                               data=dumps(put_project),
                               headers={'Authorization': self.make_header('admin-token'),
                                        'Content-Type': 'application/json',
                                        'If-Match': project['_etag']})
        self.assertEqual(200, resp.status_code, resp.data)

    def test_edits_by_nonowner_subscriber(self):
        """A subscriber should only be able to edit their own projects."""

        from pillar.api.utils import remove_private_keys, PillarJSONEncoder
        dumps = functools.partial(json.dumps, cls=PillarJSONEncoder)

        # Create test project.
        project = self._create_user_and_project(['subscriber'])
        project_id = project['_id']
        project_url = '/api/projects/%s' % project_id

        # Create test user.
        my_user_id = 'cafef00dbeefcafef00dbeef'
        self._create_user_with_token(['subscriber'], 'mortal-token', user_id=my_user_id)

        # Regular subscriber should not be able to do this.
        put_project = remove_private_keys(project)
        put_project['name'] = 'Болту́н -- нахо́дка для шпио́на.'
        put_project['user'] = my_user_id
        resp = self.client.put(project_url,
                               data=dumps(put_project),
                               headers={'Authorization': self.make_header('mortal-token'),
                                        'Content-Type': 'application/json',
                                        'If-Match': project['_etag']})
        self.assertEqual(403, resp.status_code, resp.data)

    def test_delete_by_admin(self):
        # Create public test project.
        project_info = self._create_user_and_project(['admin', 'demo'])
        project_id = project_info['_id']
        project_url = '/api/projects/%s' % project_id

        # Create admin user that doesn't own the project, to check that
        # non-owner admins can delete projects too.
        self._create_user_with_token(['admin'], 'admin-token',
                                     user_id='cafef00dbeefcafef00dbeef')

        # Admin user should be able to DELETE.
        resp = self.client.delete(project_url,
                                  headers={'Authorization': self.make_header('admin-token'),
                                           'If-Match': project_info['_etag']})
        self.assertEqual(204, resp.status_code, resp.data)

        # Check that the project is gone.
        resp = self.client.get(project_url)
        self.assertEqual(404, resp.status_code, resp.data)

        # ... but we should still get it in the body.
        db_proj = json.loads(resp.data)
        self.assertEqual('Prøject El Niño', db_proj['name'])
        self.assertTrue(db_proj['_deleted'])

        # Querying for deleted projects should include it.
        # TODO: limit this to admin users only.
        # Also see http://python-eve.org/features.html#soft-delete
        projection = json.dumps({'name': 1, 'permissions': 1})
        where = json.dumps({'_deleted': True})  # MUST be True, 1 does not work.
        resp = self.client.get('/api/projects?where=%s&projection=%s' %
                               (urllib.parse.quote(where), urllib.parse.quote(projection)))
        self.assertEqual(200, resp.status_code, resp.data)

        projlist = json.loads(resp.data)
        self.assertEqual(1, projlist['_meta']['total'])
        self.assertEqual('Prøject El Niño', projlist['_items'][0]['name'])

    def test_delete_by_subscriber(self):
        # Create test project.
        project_info = self._create_user_and_project(['subscriber'])
        project_id = project_info['_id']
        project_url = '/api/projects/%s' % project_id

        # Create test user.
        self._create_user_with_token(['subscriber'], 'mortal-token',
                                     user_id='cafef00dbeefcafef00dbeef')

        # Other user should NOT be able to DELETE.
        resp = self.client.delete(project_url,
                                  headers={'Authorization': self.make_header('mortal-token'),
                                           'If-Match': project_info['_etag']})
        self.assertEqual(403, resp.status_code, resp.data)

        # Owner should be able to DELETE
        resp = self.client.delete(project_url,
                                  headers={'Authorization': self.make_header('token'),
                                           'If-Match': project_info['_etag']})
        self.assertEqual(204, resp.status_code, resp.data)

    def test_delete_files_too(self):
        # Create test project with a file.
        project_info = self._create_user_and_project(['subscriber'])
        project_id = project_info['_id']

        fid, _ = self.ensure_file_exists({'project': ObjectId(project_id)})
        with self.app.app_context():
            files_coll = self.app.db('files')
            nowish = datetime.datetime.now(tz=bson.tz_util.utc) - datetime.timedelta(seconds=5)
            db_file_before = files_coll.find_one_and_update({'_id': fid},
                                                            {'$set': {'_updated': nowish}},
                                                            return_document=ReturnDocument.AFTER)

        # DELETE by owner should also soft-delete the file documents.
        self.delete(f'/api/projects/{project_id}',
                    auth_token='token', etag=project_info['_etag'],
                    expected_status=204)

        resp = self.get(f'/api/files/{fid}', expected_status=404)
        self.assertEqual(str(fid), resp.json()['_id'])

        with self.app.app_context():
            db_file_after = files_coll.find_one(fid)
        self.assertGreater(db_file_after['_updated'], db_file_before['_updated'])
        self.assertNotEqual(db_file_after['_etag'], db_file_before['_etag'])

    def _create_delete_project(self):
        """Create and then delete a project."""

        from pillar.api.utils import remove_private_keys
        # Create test project with a file.
        project_info = self._create_user_and_project(['subscriber'])
        project_id = project_info['_id']
        proj_url = f'/api/projects/{project_id}'
        etag = project_info['_etag']

        # Assign the file as picture_header so that we have a nice circular reference.
        fid, _ = self.ensure_file_exists({'project': ObjectId(project_id)})
        project_info['picture_header'] = str(fid)
        resp = self.put(proj_url, auth_token='token', etag=etag,
                        json=remove_private_keys(project_info))
        etag = resp.json()['_etag']

        # DELETE the project.
        self.delete(proj_url, auth_token='token', etag=etag, expected_status=204)

        with self.app.app_context():
            files_coll = self.app.db('files')
            now = datetime.datetime.now(tz=bson.tz_util.utc) - datetime.timedelta(seconds=5)
            db_file_before = files_coll.find_one_and_update({'_id': fid},
                                                            {'$set': {'_updated': now}},
                                                            return_document=ReturnDocument.AFTER)
        return db_file_before, fid, proj_url

    def test_undelete_with_patch(self):
        db_file_before, fid, proj_url = self._create_delete_project()

        # PATCH on the project should also restore the files.
        self.patch(proj_url, auth_token='token', json={'op': 'undelete'}, expected_status=204)

        resp = self.get(f'/api/files/{fid}')
        self.assertEqual(str(fid), resp.json()['_id'])

        with self.app.app_context():
            files_coll = self.app.db('files')
            db_file_after = files_coll.find_one(fid)
        self.assertGreater(db_file_after['_updated'], db_file_before['_updated'])
        self.assertNotEqual(db_file_after['_etag'], db_file_before['_etag'])

    def test_undelete_other_user(self):
        _, fid, proj_url = self._create_delete_project()

        self.create_user(user_id='baddf00dbaddf00dbaddf00d', token='baduser')

        # PATCH on the project should be denied.
        self.patch(proj_url, auth_token='baduser', json={'op': 'undelete'}, expected_status=403)

        self.get(f'/api/files/{fid}', expected_status=404)

        with self.app.app_context():
            files_coll = self.app.db('files')
            db_file_after = files_coll.find_one(fid)
        self.assertTrue(db_file_after['_deleted'])

        resp = self.get(proj_url, auth_token='token', expected_status=404).json()
        self.assertTrue(resp['_deleted'])


class ProjectNodeAccess(AbstractProjectTest):
    def setUp(self, **kwargs):
        super(ProjectNodeAccess, self).setUp(**kwargs)

        from pillar.api.utils import PillarJSONEncoder

        # Project is created by regular subscriber, so should be private.
        self.user_id = self._create_user_with_token(['subscriber'], 'token')
        resp = self._create_project('Prøject El Niño', 'token')
        self.assertEqual(201, resp.status_code)
        self.assertEqual('application/json', resp.mimetype)
        self.project = json.loads(resp.data)
        self.project_id = ObjectId(self.project['_id'])

        self.other_user_id = self._create_user_with_token(['subscriber'], 'other-token',
                                                          user_id='deadbeefdeadbeefcafef00d')

        self.test_node = {
            'description': '',
            'node_type': 'asset',
            'user': self.user_id,
            'properties': {
                'status': 'published',
                'content_type': 'image',
            },
            'name': 'Micak is a cool cat',
            'project': self.project_id,
        }

        # Add a node to the project
        resp = self.client.post('/api/nodes',
                                headers={'Authorization': self.make_header('token'),
                                         'Content-Type': 'application/json'},
                                data=json.dumps(self.test_node, cls=PillarJSONEncoder),
                                )
        self.assertEqual(201, resp.status_code, (resp.status_code, resp.data))
        self.node_info = json.loads(resp.data)
        self.node_id = self.node_info['_id']
        self.node_url = '/api/nodes/%s' % self.node_id

    def test_node_access(self):
        """Getting nodes should adhere to project access rules."""

        # Getting the node as the project owner should work.
        resp = self.client.get(self.node_url,
                               headers={'Authorization': self.make_header('token')})
        self.assertEqual(200, resp.status_code, (resp.status_code, resp.data))

        # Getting the node as an outsider should not work.
        resp = self.client.get(self.node_url,
                               headers={'Authorization': self.make_header('other-token')})
        self.assertEqual(403, resp.status_code, (resp.status_code, resp.data))

    def test_node_resource_access(self):
        # The owner of the project should get the node.
        resp = self.client.get('/api/nodes',
                               headers={'Authorization': self.make_header('token')})
        self.assertEqual(200, resp.status_code, (resp.status_code, resp.data))
        listed_nodes = json.loads(resp.data)['_items']
        self.assertEqual(self.node_id, listed_nodes[0]['_id'])

        # Listing all nodes should not include nodes from private projects.
        resp = self.client.get('/api/nodes',
                               headers={'Authorization': self.make_header('other-token')})
        self.assertEqual(403, resp.status_code, (resp.status_code, resp.data))

    def test_is_private_updated_by_world_permissions(self):
        """For backward compatibility, is_private should reflect absence of world-GET"""

        from pillar.api.utils import remove_private_keys, dumps

        project_url = '/api/projects/%s' % self.project_id
        put_project = remove_private_keys(self.project)

        # Create admin user.
        self._create_user_with_token(['admin'], 'admin-token', user_id='cafef00dbeefcafef00dbeef')

        # Make the project public
        put_project['permissions']['world'] = ['GET']  # make public
        put_project['is_private'] = True  # This should be overridden.

        resp = self.client.put(project_url,
                               data=dumps(put_project),
                               headers={'Authorization': self.make_header('admin-token'),
                                        'Content-Type': 'application/json',
                                        'If-Match': self.project['_etag']})
        self.assertEqual(200, resp.status_code, resp.data)

        with self.app.test_request_context():
            projects = self.app.data.driver.db['projects']
            db_proj = projects.find_one(self.project_id)
            self.assertEqual(['GET'], db_proj['permissions']['world'])
            self.assertFalse(db_proj['is_private'])

        # Make the project private
        put_project['permissions']['world'] = []

        resp = self.client.put(project_url,
                               data=dumps(put_project),
                               headers={'Authorization': self.make_header('admin-token'),
                                        'Content-Type': 'application/json',
                                        'If-Match': db_proj['_etag']})
        self.assertEqual(200, resp.status_code, resp.data)

        with self.app.test_request_context():
            projects = self.app.data.driver.db['projects']
            db_proj = projects.find_one(self.project_id)
            self.assertEqual([], db_proj['permissions']['world'])
            self.assertTrue(db_proj['is_private'])

    def test_add_remove_user(self):
        from pillar.api.projects import utils as proj_utils
        from pillar.api.utils import dumps

        project_mng_user_url = '/api/p/users'

        # Use our API to add user to group
        payload = {
            'project_id': self.project_id,
            'user_id': self.other_user_id,
            'action': 'add'}

        resp = self.client.post(project_mng_user_url,
                                data=dumps(payload),
                                content_type='application/json',
                                headers={
                                    'Authorization': self.make_header('token'),
                                    'If-Match': self.project['_etag']})
        self.assertEqual(200, resp.status_code, resp.data)

        # Check if the user is now actually member of the group.
        with self.app.test_request_context():
            users = self.app.data.driver.db['users']

            db_user = users.find_one(self.other_user_id)
            admin_group = proj_utils.get_admin_group(self.project)

            self.assertIn(admin_group['_id'], db_user['groups'])

        # Update payload to remove the user we just added
        payload['action'] = 'remove'

        resp = self.client.post(project_mng_user_url,
                                data=dumps(payload),
                                content_type='application/json',
                                headers={
                                    'Authorization': self.make_header('token'),
                                    'If-Match': self.project['_etag']})
        self.assertEqual(200, resp.status_code, resp.data)

        # Check if the user is now actually removed from the group.
        with self.app.test_request_context():
            users = self.app.data.driver.db['users']

            db_user = users.find_one(self.other_user_id)
            self.assertNotIn(admin_group['_id'], db_user['groups'])

    def test_remove_self(self):
        """Every user should be able to remove themselves from a project,
         regardless of permissions.
         """

        from pillar.api.projects import utils as proj_utils
        from pillar.api.utils import dumps

        project_mng_user_url = '/api/p/users'

        # Use our API to add user to group
        payload = {
            'project_id': self.project_id,
            'user_id': self.other_user_id,
            'action': 'add'}

        resp = self.client.post(project_mng_user_url,
                                data=dumps(payload),
                                content_type='application/json',
                                headers={'Authorization': self.make_header('token')})
        self.assertEqual(200, resp.status_code, resp.data)

        # Update payload to remove the user we just added, and call it as that user.
        payload['action'] = 'remove'

        resp = self.client.post(project_mng_user_url,
                                data=dumps(payload),
                                content_type='application/json',
                                headers={'Authorization': self.make_header('other-token')})
        self.assertEqual(200, resp.status_code, resp.data)

        # Check if the user is now actually removed from the group.
        with self.app.test_request_context():
            users = self.app.data.driver.db['users']

            db_user = users.find_one(self.other_user_id)
            admin_group = proj_utils.get_admin_group(self.project)
            self.assertNotIn(admin_group['_id'], db_user['groups'])
