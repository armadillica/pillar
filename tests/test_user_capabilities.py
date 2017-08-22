from pillar.tests import PillarTestServer, AbstractPillarTest


class UserCapsTestServer(PillarTestServer):
    def __init__(self, *args, **kwargs):
        PillarTestServer.__init__(self, *args, **kwargs)

        from pillar.extension import PillarExtension

        # Late-declare this class, so that it is recreated for each unit test.
        class UserCapsTestExtension(PillarExtension):
            user_roles = {
                'test-user',
                'test-မျောက်',
            }
            user_caps = {
                'subscriber': {'extra-sub-cap', 'another-cap'},
                'test-user': {'test-user-cap-1', 'နဂါးမောက်သီး'},
                'test-မျောက်': {'test-monkey-cap-1', 'နဂါးမောက်သီး'},
            }

            @property
            def name(self):
                return 'test_user_caps'

            def flask_config(self):
                return {}

            def eve_settings(self):
                return {}

            def blueprints(self):
                return []

        self.load_extension(UserCapsTestExtension(), '/user-caps-test')


class UserCapsTest(AbstractPillarTest):
    pillar_server_class = UserCapsTestServer

    def setUp(self, **kwargs):
        super().setUp(**kwargs)

    def tearDown(self):
        super().tearDown()

    def test_default_caps(self):
        app_caps = self.app.user_caps

        self.assertEqual(app_caps['demo'], frozenset({
            'subscriber', 'home-project'
        }))

    def test_aggr_caps_merged_subscriber(self):
        app_caps = self.app.user_caps

        self.assertEqual(app_caps['subscriber'], frozenset({
            'subscriber', 'home-project', 'extra-sub-cap', 'another-cap'
        }))

    def test_aggr_caps_new_roles(self):
        app_caps = self.app.user_caps

        self.assertEqual(app_caps['test-user'], frozenset({
            'test-user-cap-1', 'နဂါးမောက်သီး'
        }))

        self.assertEqual(app_caps['test-မျောက်'], frozenset({
            'test-monkey-cap-1', 'နဂါးမောက်သီး'
        }))
