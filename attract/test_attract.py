import os
import json
import unittest
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime


class AttractTestCase(unittest.TestCase):

    def addUser(self, firstname, lastname, role):
        return self.app.post('/users', data=dict(
            firstname=firstname,
            lastname=lastname,
            role=role,
        ), follow_redirects=True)

    def addNodeType(self, name, schema):
        data = {
            'name': name,
            'dyn_schema': schema,
        }
        headers = {
            'content-type': 'application/json',
            'Authorization': 'Basic QU5MR05TSUVaSjoxMjM0'
        }
        return self.app.post(
           '/node_types',
            data=json.dumps(data),
            headers=headers,
            follow_redirects=True)

    def addNode(self, name, nodeType, properties):
        data = {
            'name': name,
            'node_type': nodeType,
            'properties': properties
        }
        headers = {
            'content-type': 'application/json',
            'Authorization': 'Basic QU5MR05TSUVaSjoxMjM0',
        }
        return self.app.post(
           '/nodes',
            data=json.dumps(data),
            headers=headers,
            follow_redirects=True)

    def logout(self):
        return self.app.get('/logout', follow_redirects=True)


    # Tests

    def test_add_user(self):
        rv = self.addUser('admin', 'default', 'author')
        assert 201 == rv.status_code

    def test_add_node_type(self):
        schema = {
            'frame_start': {
                'type':'integer',
            }
        }
        rv = self.addNodeType('NodeName', schema)
        assert 201 == rv.status_code

    def test_add_node(self):
        properties = {
            'frame_start': 123
        }
        rv = self.addNode('Shot01', '55016a52135d32466fc800be', properties)
        assert 201 == rv.status_code

    def test_empty_db(self):
        rv = self.app.get('/')
        assert 401 == rv.status_code

    # Test Setup

    def setUp(self):
        # Setup DB
        client = MongoClient()
        db = client.attract_test
        for col in db.collection_names():
            try:
                db[col].remove({})
            except:
                pass

        test_user = {
            "_id": ObjectId("550171c8135d3248e477f288"),
            "_updated": datetime.now(),
            "firstname": "TestFirstname",
            "lastname": "TestLastname",
            "token": "ANLGNSIEZJ",
            "role": "author",
            "_created": datetime.now(),
            "_etag": "302236e27f51d2e26041ae9de49505d77332b260"
            }

        test_node_type = {
            "_id": ObjectId("55016a52135d32466fc800be"),
            "_updated": datetime.now(),
            "name": "NodeName",
            "dyn_schema": {"frame_start": {"type": "integer"}},
            "_created": datetime.now(),
            "_etag": "0ea3c4f684a0cda85525184d5606c4f4ce6ac5f5"
            }

        db.users.insert(test_user)
        db.node_types.insert(test_node_type)

        # Initialize Attract
        os.environ['TEST_ATTRACT'] = '1'
        import application
        application.app.config['TESTING'] = True
        self.app = application.app.test_client()

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
