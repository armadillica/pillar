import unittest

import flask


class FlaskExtraTest(unittest.TestCase):
    def test_vary_xhr(self):
        import pillar.flask_extra

        class TestApp(flask.Flask):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

                self.add_url_rule('/must-vary', 'must-vary', self.must_vary)
                self.add_url_rule('/no-vary', 'no-vary', self.no_vary)

            @pillar.flask_extra.vary_xhr()
            def must_vary(self):
                return 'yay'

            def no_vary(self):
                return 'nah', 201

        app = TestApp(__name__)
        client = app.test_client()

        resp = client.get('/must-vary')
        self.assertEqual(200, resp.status_code)
        self.assertEqual('X-Requested-With', resp.headers['Vary'])
        self.assertEqual('yay', resp.data.decode())

        resp = client.get('/no-vary')
        self.assertEqual(201, resp.status_code)
        self.assertNotIn('Vary', resp.headers)
        self.assertEqual('nah', resp.data.decode())


class EnsureSchemaTest(unittest.TestCase):
    def test_ensure_schema_http(self):
        import pillar.flask_extra

        suffix = '://user:password@hostname/some-path/%2Fpaththing?query=abc#fragment'

        app = flask.Flask(__name__)
        app.config['PREFERRED_URL_SCHEME'] = 'http'
        with app.app_context():
            for scheme in ('http', 'https', 'ftp', 'gopher'):
                self.assertEqual(
                    f'http{suffix}',
                    pillar.flask_extra.ensure_schema(f'{scheme}{suffix}'))

    def test_ensure_schema_https(self):
        import pillar.flask_extra

        suffix = '://user:password@hostname/some-path/%2Fpaththing?query=abc#fragment'

        app = flask.Flask(__name__)
        app.config['PREFERRED_URL_SCHEME'] = 'https'
        with app.app_context():
            for scheme in ('http', 'https', 'ftp', 'gopher'):
                self.assertEqual(
                    f'https{suffix}',
                    pillar.flask_extra.ensure_schema(f'{scheme}{suffix}'))

    def test_no_config(self):
        import pillar.flask_extra

        suffix = '://user:password@hostname/some-path/%2Fpaththing?query=abc#fragment'

        app = flask.Flask(__name__)
        app.config.pop('PREFERRED_URL_SCHEME', None)
        with app.app_context():
            self.assertEqual(
                f'https{suffix}',
                pillar.flask_extra.ensure_schema(f'gopher{suffix}'))

    def test_corner_cases(self):
        import pillar.flask_extra

        app = flask.Flask(__name__)
        app.config['PREFERRED_URL_SCHEME'] = 'https'
        with app.app_context():
            self.assertEqual('', pillar.flask_extra.ensure_schema(''))
            self.assertEqual('/some/path/only', pillar.flask_extra.ensure_schema('/some/path/only'))
            self.assertEqual('https://hostname/path',
                             pillar.flask_extra.ensure_schema('//hostname/path'))
