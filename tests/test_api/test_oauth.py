import responses
from pillar.tests import AbstractPillarTest


class OAuthTests(AbstractPillarTest):
    def setUp(self, **kwargs):
        super().setUp(**kwargs)
        self.enter_app_context()

    def test_providers_init(self):
        from pillar.auth.oauth import OAuthSignIn, BlenderIdSignIn

        oauth_provider = OAuthSignIn.get_provider('blender-id')
        self.assertIsInstance(oauth_provider, BlenderIdSignIn)
        self.assertEqual(oauth_provider.service.base_url, 'http://blender_id:8000/api/')

    def test_provider_not_implemented(self):
        from pillar.auth.oauth import OAuthSignIn, ProviderNotImplemented

        with self.assertRaises(ProviderNotImplemented):
            OAuthSignIn.get_provider('jonny')

    def test_provider_not_configured(self):
        from pillar.auth.oauth import OAuthSignIn, ProviderConfigurationMissing

        # Before we start this test, the providers dict
        # may not be initialized yet.
        self.assertIsNone(OAuthSignIn._providers)

        del self.app.config['OAUTH_CREDENTIALS']['blender-id']
        with self.assertRaises(ProviderConfigurationMissing):
            OAuthSignIn.get_provider('blender-id')

    def test_provider_authorize(self):
        from pillar.auth.oauth import OAuthSignIn
        from urllib.parse import urlparse, parse_qsl
        oauth_provider = OAuthSignIn.get_provider('blender-id')
        r = oauth_provider.authorize()
        self.assertEqual(r.status_code, 302)
        url_parts = list(urlparse(r.location))
        # Get the query arguments as a dict
        query = dict(parse_qsl(url_parts[4]))
        self.assertEqual(query['client_id'], oauth_provider.service.client_id)

    @responses.activate
    def test_provider_callback_happy(self):
        from pillar.auth.oauth import OAuthSignIn

        responses.add(responses.POST, 'http://blender_id:8000/oauth/token',
                      json={'access_token': 'successful-token'},
                      status=200)

        responses.add(responses.GET, 'http://blender_id:8000/api/user',
                      json={'id': '7',
                            'email': 'harry@blender.org'},
                      status=200)

        oauth_provider = OAuthSignIn.get_provider('blender-id')

        with self.app.test_request_context('/oauth/blender-id/authorized?code=123'):
            # We override the call to blender-id
            cb = oauth_provider.callback()
            self.assertEqual(cb.id, '7')

    @responses.activate
    def test_provider_callback_missing_code(self):
        from pillar.auth.oauth import OAuthSignIn, OAuthCodeNotProvided

        oauth_provider = OAuthSignIn.get_provider('blender-id')

        # Check exception when the 'code' argument is not returned
        with self.assertRaises(OAuthCodeNotProvided):
            with self.app.test_request_context('/oauth/blender-id/authorized'):
                oauth_provider.callback()

