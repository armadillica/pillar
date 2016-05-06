# -*- encoding: utf-8 -*-

"""Unit tests for creating and editing projects_blueprint."""

import functools
import json
import logging
import urllib

from bson import ObjectId

from common_test_class import AbstractPillarTest

log = logging.getLogger(__name__)


class AbstractProjectTest(AbstractPillarTest):
    def _create_user_with_token(self, roles, token, user_id='cafef00df00df00df00df00d'):
        user_id = self.create_user(roles=roles, user_id=user_id)
        self.create_valid_auth_token(user_id, token)
        return user_id

    def _create_project(self, project_name, token):
        resp = self.client.post('/p/create',
                                headers={'Authorization': self.make_header(token)},
                                data={'project_name': project_name})
        return resp

    def _create_user_and_project(self, roles):
        self._create_user_with_token(roles, 'token')
        resp = self._create_project(u'Prøject El Niño', 'token')

        self.assertEqual(201, resp.status_code, resp.data)
        project = json.loads(resp.data)

        return project


class ProjectCreationTest(AbstractProjectTest):
    def test_project_creation_wrong_role(self):
        self._create_user_with_token([u'whatever'], 'token')
        resp = self._create_project(u'Prøject El Niño', 'token')

        self.assertEqual(403, resp.status_code)

        # Test that the project wasn't created.
        with self.app.test_request_context():
            projects = self.app.data.driver.db['projects']
            self.assertEqual(0, len(list(projects.find())))

    def test_project_creation_good_role(self):
        user_id = self._create_user_with_token([u'subscriber'], 'token')
        resp = self._create_project(u'Prøject El Niño', 'token')
        self.assertEqual(201, resp.status_code)

        # The response of a POST is the entire project, but we'll test a GET on
        # the returned Location nevertheless.
        project_info = json.loads(resp.data.decode('utf-8'))
        project_id = project_info['_id']

        # Test that the Location header contains the location of the project document.
        self.assertEqual('http://localhost/projects/%s' % project_id,
                         resp.headers['Location'])

        # GET the project from the URL in the Location header to see if that works too.
        auth_header = {'Authorization': self.make_header('token')}
        resp = self.client.get(resp.headers['Location'], headers=auth_header)
        project = json.loads(resp.data.decode('utf-8'))
        project_id = project['_id']

        # Check some of the more complex/interesting fields.
        self.assertEqual(u'Prøject El Niño', project['name'])
        self.assertEqual(str(user_id), project['user'])
        self.assertEqual('p-%s' % project_id, project['url'])
        self.assertEqual(1, len(project['permissions']['groups']))

        # Check the etag
        resp = self.client.get('/projects/%s' % project_id, headers=auth_header)
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

        proj = self._create_user_and_project(roles={u'admin'})
        self.assertEqual(['GET'], proj['permissions']['world'])

    def test_project_creation_access_subscriber(self):
        """Subscriber-created projects should be private"""

        proj = self._create_user_and_project(roles={u'subscriber'})
        self.assertEqual([], proj['permissions']['world'])


class ProjectEditTest(AbstractProjectTest):
    def test_editing_as_subscriber(self):
        """Test that we can set certain fields, but not all."""

        from application.utils import remove_private_keys, PillarJSONEncoder
        dumps = functools.partial(json.dumps, cls=PillarJSONEncoder)

        project_info = self._create_user_and_project([u'subscriber'])
        project_url = '/projects/%(_id)s' % project_info

        resp = self.client.get(project_url,
                               headers={'Authorization': self.make_header('token')})
        project = json.loads(resp.data.decode('utf-8'))

        # Create another user we can try and assign the project to.
        other_user_id = 'f00dd00df00dd00df00dd00d'
        self._create_user_with_token(['subscriber'], 'other-token', user_id=other_user_id)

        # Unauthenticated should be forbidden
        resp = self.client.put('/projects/%s' % project['_id'],
                               data=dumps(remove_private_keys(project)),
                               headers={'Content-Type': 'application/json'})
        self.assertEqual(403, resp.status_code)

        # Regular user should be able to PUT, but only be able to edit certain fields.
        put_project = remove_private_keys(project)
        put_project['url'] = u'very-offensive-url'
        put_project['description'] = u'Blender je besplatan set alata za izradu interaktivnog 3D ' \
                                     u'sadržaja pod različitim operativnim sustavima.'
        put_project['name'] = u'โครงการปั่นเมฆ'
        put_project['summary'] = u'Это переведена на Google'
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
        resp = self.client.get(project_url,
                               headers={'Authorization': self.make_header('token')})
        db_proj = json.loads(resp.data)
        self.assertEqual(project['url'], db_proj['url'])
        self.assertEqual(put_project['description'], db_proj['description'])
        self.assertEqual(put_project['name'], db_proj['name'])
        self.assertEqual(put_project['summary'], db_proj['summary'])
        self.assertEqual(project['is_private'], db_proj['is_private'])
        self.assertEqual(project['status'], db_proj['status'])
        self.assertEqual(project['category'], db_proj['category'])

    def test_editing_as_admin(self):
        """Test that we can set all fields as admin."""

        from application.utils import remove_private_keys, PillarJSONEncoder
        dumps = functools.partial(json.dumps, cls=PillarJSONEncoder)

        project_info = self._create_user_and_project([u'subscriber', u'admin'])
        project_url = '/projects/%(_id)s' % project_info

        resp = self.client.get(project_url)
        project = json.loads(resp.data.decode('utf-8'))

        # Create another user we can try and assign the project to.
        other_user_id = 'f00dd00df00dd00df00dd00d'
        self._create_user_with_token(['subscriber'], 'other-token', user_id=other_user_id)

        # Admin user should be able to PUT everything.
        put_project = remove_private_keys(project)
        put_project['url'] = u'very-offensive-url'
        put_project['description'] = u'Blender je besplatan set alata za izradu interaktivnog 3D ' \
                                     u'sadržaja pod različitim operativnim sustavima.'
        put_project['name'] = u'โครงการปั่นเมฆ'
        put_project['summary'] = u'Это переведена на Google'
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
        resp = self.client.get('/projects/%s' % project['_id'])
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

        from application.utils import remove_private_keys, PillarJSONEncoder
        dumps = functools.partial(json.dumps, cls=PillarJSONEncoder)

        # Create test project.
        project = self._create_user_and_project([u'subscriber'])
        project_id = project['_id']
        project_url = '/projects/%s' % project_id

        # Create test user.
        self._create_user_with_token(['admin'], 'admin-token', user_id='cafef00dbeef')

        # Admin user should be able to PUT.
        put_project = remove_private_keys(project)
        put_project['name'] = u'โครงการปั่นเมฆ'

        resp = self.client.put(project_url,
                               data=dumps(put_project),
                               headers={'Authorization': self.make_header('admin-token'),
                                        'Content-Type': 'application/json',
                                        'If-Match': project['_etag']})
        self.assertEqual(200, resp.status_code, resp.data)

    def test_edits_by_nonowner_subscriber(self):
        """A subscriber should only be able to edit their own projects."""

        from application.utils import remove_private_keys, PillarJSONEncoder
        dumps = functools.partial(json.dumps, cls=PillarJSONEncoder)

        # Create test project.
        project = self._create_user_and_project([u'subscriber'])
        project_id = project['_id']
        project_url = '/projects/%s' % project_id

        # Create test user.
        my_user_id = 'cafef00dbeefcafef00dbeef'
        self._create_user_with_token(['subscriber'], 'mortal-token', user_id=my_user_id)

        # Regular subscriber should not be able to do this.
        put_project = remove_private_keys(project)
        put_project['name'] = u'Болту́н -- нахо́дка для шпио́на.'
        put_project['user'] = my_user_id
        resp = self.client.put(project_url,
                               data=dumps(put_project),
                               headers={'Authorization': self.make_header('mortal-token'),
                                        'Content-Type': 'application/json',
                                        'If-Match': project['_etag']})
        self.assertEqual(403, resp.status_code, resp.data)

    def test_delete_by_admin(self):
        # Create public test project.
        project_info = self._create_user_and_project([u'admin'])
        project_id = project_info['_id']
        project_url = '/projects/%s' % project_id

        # Create admin user that doesn't own the project, to check that
        # non-owner admins can delete projects too.
        self._create_user_with_token(['admin'], 'admin-token', user_id='cafef00dbeef')

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
        self.assertEqual(u'Prøject El Niño', db_proj['name'])
        self.assertTrue(db_proj['_deleted'])

        # Querying for deleted projects should include it.
        # TODO: limit this to admin users only.
        # Also see http://python-eve.org/features.html#soft-delete
        projection = json.dumps({'name': 1, 'permissions': 1})
        where = json.dumps({'_deleted': True})  # MUST be True, 1 does not work.
        resp = self.client.get('/projects?where=%s&projection=%s' %
                               (urllib.quote(where), urllib.quote(projection)))
        self.assertEqual(200, resp.status_code, resp.data)

        projlist = json.loads(resp.data)
        self.assertEqual(1, projlist['_meta']['total'])
        self.assertEqual(u'Prøject El Niño', projlist['_items'][0]['name'])

    def test_delete_by_subscriber(self):
        # Create test project.
        project_info = self._create_user_and_project([u'subscriber'])
        project_id = project_info['_id']
        project_url = '/projects/%s' % project_id

        # Create test user.
        self._create_user_with_token(['subscriber'], 'mortal-token', user_id='cafef00dbeef')

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


class ProjectNodeAccess(AbstractProjectTest):
    def setUp(self, **kwargs):
        super(ProjectNodeAccess, self).setUp(**kwargs)

        from application.utils import PillarJSONEncoder

        # Project is created by regular subscriber, so should be private.
        self.user_id = self._create_user_with_token([u'subscriber'], 'token')
        resp = self._create_project(u'Prøject El Niño', 'token')
        self.assertEqual(201, resp.status_code)
        self.assertEqual('application/json', resp.mimetype)
        self.project = json.loads(resp.data)
        self.project_id = ObjectId(self.project['_id'])

        self._create_user_with_token([u'subscriber'], 'other-token',
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
        resp = self.client.post('/nodes',
                                headers={'Authorization': self.make_header('token'),
                                         'Content-Type': 'application/json'},
                                data=json.dumps(self.test_node, cls=PillarJSONEncoder),
                                )
        self.assertEqual(201, resp.status_code, (resp.status_code, resp.data))
        self.node_info = json.loads(resp.data)
        self.node_id = self.node_info['_id']
        self.node_url = '/nodes/%s' % self.node_id

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
        resp = self.client.get('/nodes',
                               headers={'Authorization': self.make_header('token')})
        self.assertEqual(200, resp.status_code, (resp.status_code, resp.data))
        listed_nodes = json.loads(resp.data)['_items']
        self.assertEquals(self.node_id, listed_nodes[0]['_id'])

        # Listing all nodes should not include nodes from private projects.
        resp = self.client.get('/nodes',
                               headers={'Authorization': self.make_header('other-token')})
        self.assertEqual(403, resp.status_code, (resp.status_code, resp.data))

    def test_is_private_updated_by_world_permissions(self):
        """For backward compatibility, is_private should reflect absence of world-GET"""

        from application.utils import remove_private_keys, dumps

        project_url = '/projects/%s' % self.project_id
        put_project = remove_private_keys(self.project)

        # Create admin user.
        self._create_user_with_token(['admin'], 'admin-token', user_id='cafef00dbeef')

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
        project_add_user_url = '/p/users'

        # Create another user we can try to share the project with
        other_user_id = 'f00dd00df00dd00df00dd00d'
        self._create_user_with_token(['subscriber'], 'other-token',
                                     user_id=other_user_id)

        # Use our API to add user to group
        payload = {
            'project_id': self.project_id,
            'user_id': other_user_id,
            'action': 'add'}

        resp = self.client.post(project_add_user_url,
                                data=json.dumps(payload),
                                content_type='application/json',
                                headers={
                                    'Authorization': self.make_header('token'),
                                    'If-Match': self.project['_etag']})
        self.assertEqual(200, resp.status_code, resp.data)

        with self.app.test_request_context():
            groups = self.app.data.driver.db['groups']
            users = self.app.data.driver.db['users']

            # Get other_user document
            db_user = users.find_one(ObjectId(other_user_id))

            # Get the admin group (has same name as project id)
            # TODO: handle case when user has multiple groups
            admin_group_id = db_user['groups'][0]
            admin_group = groups.find_one({'_id': admin_group_id})

            # Check if admin group name matches
            self.assertEqual(admin_group['name'], str(self.project['_id']))

        # Update payload to remove the user we just added
        payload['action'] = 'remove'

        resp = self.client.post(project_add_user_url,
                                data=json.dumps(payload),
                                content_type='application/json',
                                headers={
                                    'Authorization': self.make_header('token'),
                                    'If-Match': self.project['_etag']})
        self.assertEqual(200, resp.status_code, resp.data)

