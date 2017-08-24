from pillar.tests import AbstractPillarTest


class OAuthTests(AbstractPillarTest):
    def setUp(self, **kwargs):
        super().setUp(**kwargs)
        self.enter_app_context()

    def test_providers_init(self):
        from pillar.auth.oauth import OAuthSignIn, BlenderIdSignIn

        blender_id_oauth_provider = OAuthSignIn.get_provider('blender-id')
        self.assertIsInstance(blender_id_oauth_provider, BlenderIdSignIn)
        self.assertEqual(blender_id_oauth_provider.service.base_url, 'http://blender_id:8000/api/')

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
