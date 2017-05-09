from pillar.tests import AbstractPillarTest


class PatchHandlerTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        super().setUp(**kwargs)
        import flask
        from pillar.api import patch_handler

        # Create a patch handler and register it.
        class BogusPatchHandler(patch_handler.AbstractPatchHandler):
            item_name = 'gremlin'

            def patch_test_echo(self, op: str, patch: dict):
                return flask.jsonify({'echo': patch['echo']})

            def patch_test_empty(self, op: str, patch: dict):
                return None

        blueprint = flask.Blueprint('test_patch_handler', __name__)
        self.patch_handler = BogusPatchHandler(blueprint)

        self.app.register_api_blueprint(blueprint, url_prefix='/test')

        # Patching always requires a logged-in user.
        self.user_id = self.create_user(token='user-token')

    def test_patch_anonymous(self):
        import bson

        oid = bson.ObjectId()
        self.patch('/api/test/%s' % oid, expected_status=403)

    def test_patch_without_json(self):
        import bson

        oid = bson.ObjectId()
        self.patch('/api/test/%s' % oid, auth_token='user-token', expected_status=400)

    def test_patch_no_operation(self):
        import bson

        oid = bson.ObjectId()
        self.patch('/api/test/%s' % oid, auth_token='user-token',
                   json={'je': 'moeder'},
                   expected_status=400)

    def test_patch_invalid_operation(self):
        import bson

        oid = bson.ObjectId()
        self.patch('/api/test/%s' % oid, auth_token='user-token',
                   json={'op': 'snowcrash'},
                   expected_status=400)

    def test_patch_happy(self):
        import bson

        oid = bson.ObjectId()
        resp = self.patch('/api/test/%s' % oid, auth_token='user-token',
                          json={'op': 'test-echo',
                                'echo': '¡Thith ith Špahtah!'})
        self.assertEqual({'echo': '¡Thith ith Špahtah!'}, resp.json())

    def test_patch_empty_response(self):
        import bson

        oid = bson.ObjectId()
        resp = self.patch('/api/test/%s' % oid, auth_token='user-token',
                          json={'op': 'test-empty',
                                'echo': '¡Thith ith Špahtah!'},
                          expected_status=204)
        self.assertEqual(b'', resp.data)


class PatchHandlerCreationTest(AbstractPillarTest):
    def test_without_route(self):
        from pillar.api import patch_handler

        with self.assertRaises(ValueError):
            class BogusPatchHandler(patch_handler.AbstractPatchHandler):
                route = ''

    def test_without_item_name(self):
        from pillar.api import patch_handler

        with self.assertRaises(ValueError):
            class BogusPatchHandler(patch_handler.AbstractPatchHandler):
                pass
