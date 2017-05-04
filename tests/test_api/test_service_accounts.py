import json

from pillar.tests import AbstractPillarTest


class ServiceAccountCreationTest(AbstractPillarTest):
    def test_create_service_account(self):
        from pillar.api.utils.authentication import force_cli_user
        from pillar.api import service

        with self.app.test_request_context():
            force_cli_user()
            account, token = service.create_service_account(
                'jemoeder@jevader.nl', ['flamenco_manager'], {'flamenco_manager': {}})

        self.assertEqual(f'SRV-{account["_id"]}', account['full_name'])
        self.assertEqual(f'SRV-{account["_id"]}', account['username'])
        self.assertEqual(['flamenco_manager', 'service'], account['roles'])
        self.assertEqual([], account['auth'])
        self.assertEqual({'flamenco_manager': {}}, account['service'])

        self.assertAllowsAccess(token, account['_id'])

    def test_without_email_address(self):
        from pillar.api.utils.authentication import force_cli_user
        from pillar.api.service import create_service_account as create_sa

        with self.app.test_request_context():
            force_cli_user()
            account, token = create_sa('', ['flamenco_manager'], {'flamenco_manager': {}})

        self.assertNotIn('email', account)
        self.assertAllowsAccess(token, account['_id'])

    def test_two_without_email_address(self):
        from pillar.api.utils.authentication import force_cli_user
        from pillar.api.service import create_service_account as create_sa

        with self.app.test_request_context():
            force_cli_user()

            account1, token1 = create_sa('', ['flamenco_manager'], {'flamenco_manager': {}})
            account2, token2 = create_sa('', ['flamenco_manager'], {'flamenco_manager': {}})

        self.assertAllowsAccess(token1, account1['_id'])
        self.assertAllowsAccess(token2, account2['_id'])

    def test_put_without_email_address(self):
        from pillar.api.utils import remove_private_keys
        from pillar.api.utils.authentication import force_cli_user
        from pillar.api.service import create_service_account as create_sa

        with self.app.test_request_context():
            force_cli_user()
            account, token = create_sa('', ['flamenco_manager'], {'flamenco_manager': {}})

        puttable = remove_private_keys(account)
        user_id = account['_id']

        # The user should be able to edit themselves, even without email address.
        etag = account['_etag']
        puttable['full_name'] = 'þor'
        resp = self.put(f'/api/users/{user_id}',
                        json=puttable,
                        auth_token=token['token'],
                        etag=etag).json()
        etag = resp['_etag']

        with self.app.test_request_context():
            users_coll = self.app.db().users
            db_user = users_coll.find_one(user_id)
            self.assertNotIn('email', db_user)
            self.assertEqual('þor', db_user['full_name'])

        # An admin should be able to edit this email-less user.
        self.create_user(24 * 'a', roles={'admin'}, token='admin-token')
        puttable['username'] = 'bigdüde'
        self.put(f'/api/users/{user_id}',
                 json=puttable,
                 auth_token='admin-token',
                 etag=etag)

        with self.app.test_request_context():
            users_coll = self.app.db().users
            db_user = users_coll.find_one(user_id)
            self.assertNotIn('email', db_user)
            self.assertEqual('bigdüde', db_user['username'])
