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
