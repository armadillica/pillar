import flask
import flask_login
from pillar.tests import AbstractPillarTest


class UsernameTest(AbstractPillarTest):
    def setUp(self, **kwargs) -> None:
        super().setUp(**kwargs)
        self.user_id = self.create_user()

    def test_update_via_web(self) -> None:
        from pillar.auth import current_user
        import pillar.web.settings.routes

        with self.app.app_context():
            url = flask.url_for('settings.profile')

        with self.app.test_request_context(
                path=url,
                data={'username': 'je.moeder'},
                method='POST',
        ):
            self.login_api_as(self.user_id)
            flask_login.login_user(current_user)
            pillar.web.settings.routes.profile()

        db_user = self.fetch_user_from_db(self.user_id)
        self.assertEqual('je.moeder', db_user['username'])

    def test_update_via_patch(self) -> None:
        self.create_valid_auth_token(self.user_id, 'user-token')
        self.patch(f'/api/users/{self.user_id}',
                   json={'op': 'set-username', 'username': 'je.moeder'},
                   auth_token='user-token')

        db_user = self.fetch_user_from_db(self.user_id)
        self.assertEqual('je.moeder', db_user['username'])
