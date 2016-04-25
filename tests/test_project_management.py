# -*- encoding: utf-8 -*-

"""Unit tests for creating and editing projects_blueprint."""

import json

import responses
from bson import ObjectId

from common_test_class import AbstractPillarTest


class ProjectCreationTest(AbstractPillarTest):
    @responses.activate
    def test_project_creation_wrong_role(self):
        user_id = self.create_user(roles=[u'whatever'])
        self.create_valid_auth_token(user_id, 'token')

        resp = self.client.post('/p/create',
                                headers={'Authorization': self.make_header('token')},
                                data={'project_name': u'Prøject El Niño'})

        self.assertEqual(403, resp.status_code)

        # Test that the project wasn't created.
        with self.app.test_request_context():
            projects = self.app.data.driver.db['projects']
            self.assertEqual(0, len(list(projects.find())))

    @responses.activate
    def test_project_creation_good_role(self):
        user_id = self.create_user(roles=[u'subscriber'])
        self.create_valid_auth_token(user_id, 'token')

        resp = self.client.post('/p/create',
                                headers={'Authorization': self.make_header('token')},
                                data={'project_name': u'Prøject El Niñö'})

        self.assertEqual(201, resp.status_code)
        project = json.loads(resp.data.decode('utf-8'))
        project_id = project['_id']

        # Test that the Location header contains the location of the project document.
        self.assertEqual('http://localhost/projects/%s' % project_id,
                         resp.headers['Location'])

        # Check some of the more complex/interesting fields.
        self.assertEqual(u'Prøject El Niñö', project['name'])
        self.assertEqual(str(user_id), project['user'])
        self.assertEqual('p-%s' % project_id, project['url'])
        self.assertEqual(1, len(project['permissions']['groups']))

        group_id = ObjectId(project['permissions']['groups'][0]['group'])

        # Check that there is a group for the project, and that the user is member of it.
        with self.app.test_request_context():
            groups = self.app.data.driver.db['groups']
            users = self.app.data.driver.db['users']

            group = groups.find_one(group_id)
            db_user = users.find_one(user_id)

            self.assertEqual(str(project_id), group['name'])
            self.assertIn(group_id, db_user['groups'])

