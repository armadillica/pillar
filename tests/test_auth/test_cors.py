from pillar.tests import AbstractPillarTest

import flask
import werkzeug.wrappers as wz_wrappers
import werkzeug.exceptions as wz_exceptions


class CorsWrapperTest(AbstractPillarTest):
    def test_noncors_request(self):
        from pillar.auth.cors import allow

        @allow()
        def wrapped(a, b):
            return f'{a} and {b}'

        with self.app.test_request_context():
            resp = wrapped('x', 'y')

        self.assertEqual('x and y', resp, 'Non-CORS request should not be modified')

    def test_string_response(self):
        from pillar.auth.cors import allow

        @allow()
        def wrapped(a, b):
            return f'{a} and {b}'

        with self.app.test_request_context(headers={'Origin': 'http://jemoeder.nl:1234/'}):
            resp = wrapped('x', 'y')

        self.assertIsInstance(resp, wz_wrappers.Response)
        self.assertEqual(b'x and y', resp.data)
        self.assertEqual(200, resp.status_code)

        self.assertEqual('http://jemoeder.nl:1234/', resp.headers['Access-Control-Allow-Origin'])
        self.assertEqual('x-requested-with', resp.headers['Access-Control-Allow-Headers'])
        self.assertNotIn('Access-Control-Allow-Credentials', resp.headers)

    def test_string_with_code_response(self):
        from pillar.auth.cors import allow

        @allow()
        def wrapped(a, b):
            return f'{a} and {b}', 403

        with self.app.test_request_context(headers={'Origin': 'http://jemoeder.nl:1234/'}):
            resp = wrapped('x', 'y')

        self.assertIsInstance(resp, wz_wrappers.Response)
        self.assertEqual(b'x and y', resp.data)
        self.assertEqual(403, resp.status_code)

        self.assertEqual('http://jemoeder.nl:1234/', resp.headers['Access-Control-Allow-Origin'])
        self.assertEqual('x-requested-with', resp.headers['Access-Control-Allow-Headers'])
        self.assertNotIn('Access-Control-Allow-Credentials', resp.headers)

    def test_flask_response_object(self):
        from pillar.auth.cors import allow

        @allow()
        def wrapped(a, b):
            return flask.Response(f'{a} and {b}', status=147, headers={'op-je': 'hoofd'})

        with self.app.test_request_context(headers={'Origin': 'http://jemoeder.nl:1234/'}):
            resp = wrapped('x', 'y')

        self.assertIsInstance(resp, wz_wrappers.Response)
        self.assertEqual(b'x and y', resp.data)
        self.assertEqual(147, resp.status_code)
        self.assertEqual('hoofd', resp.headers['Op-Je'])

        self.assertEqual('http://jemoeder.nl:1234/', resp.headers['Access-Control-Allow-Origin'])
        self.assertEqual('x-requested-with', resp.headers['Access-Control-Allow-Headers'])
        self.assertNotIn('Access-Control-Allow-Credentials', resp.headers)

    def test_wz_exception(self):
        from pillar.auth.cors import allow

        @allow()
        def wrapped(a, b):
            raise wz_exceptions.NotImplemented('nee')

        with self.app.test_request_context(headers={'Origin': 'http://jemoeder.nl:1234/'}):
            resp = wrapped('x', 'y')

        self.assertIsInstance(resp, wz_wrappers.Response)
        self.assertIn(b'nee', resp.data)
        self.assertEqual(501, resp.status_code)

        self.assertEqual('http://jemoeder.nl:1234/', resp.headers['Access-Control-Allow-Origin'])
        self.assertEqual('x-requested-with', resp.headers['Access-Control-Allow-Headers'])
        self.assertNotIn('Access-Control-Allow-Credentials', resp.headers)

    def test_flask_abort(self):
        from pillar.auth.cors import allow

        @allow()
        def wrapped(a, b):
            raise flask.abort(401)

        with self.app.test_request_context(headers={'Origin': 'http://jemoeder.nl:1234/'}):
            resp = wrapped('x', 'y')

        self.assertIsInstance(resp, wz_wrappers.Response)
        self.assertEqual(401, resp.status_code)

        self.assertEqual('http://jemoeder.nl:1234/', resp.headers['Access-Control-Allow-Origin'])
        self.assertEqual('x-requested-with', resp.headers['Access-Control-Allow-Headers'])
        self.assertNotIn('Access-Control-Allow-Credentials', resp.headers)

    def test_with_credentials(self):
        from pillar.auth.cors import allow

        @allow(allow_credentials=True)
        def wrapped(a, b):
            return f'{a} and {b}'

        with self.app.test_request_context(headers={'Origin': 'http://jemoeder.nl:1234/'}):
            resp = wrapped('x', 'y')

        self.assertIsInstance(resp, wz_wrappers.Response)
        self.assertEqual(b'x and y', resp.data)
        self.assertEqual(200, resp.status_code)

        self.assertEqual('http://jemoeder.nl:1234/', resp.headers['Access-Control-Allow-Origin'])
        self.assertEqual('x-requested-with', resp.headers['Access-Control-Allow-Headers'])
        self.assertEqual('true', resp.headers['Access-Control-Allow-Credentials'])
