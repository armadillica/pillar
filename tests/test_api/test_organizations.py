from pillar.tests import AbstractPillarTest

import bson


class OrganizationCruTest(AbstractPillarTest):
    """Test creating and updating organizations."""

    def test_create_org(self):
        self.enter_app_context()

        # There should be no organizations to begin with.
        db = self.app.db('organizations')
        self.assertEqual(0, db.count())

        admin_uid = self.create_user(24 * 'a')
        org_doc = self.app.org_manager.create_new_org('Хакеры', admin_uid, 25)

        self.assertIsNotNone(db.find_one(org_doc['_id']))
        self.assertEqual(bson.ObjectId(24 * 'a'), org_doc['admin_uid'])
        self.assertEqual('Хакеры', org_doc['name'])
        self.assertEqual(25, org_doc['seat_count'])

    def test_assign_users(self):
        self.enter_app_context()

        admin_uid = self.create_user(24 * 'a')
        member1_uid = self.create_user(24 * 'b', email='member1@example.com')

        om = self.app.org_manager
        org_doc = om.create_new_org('Хакеры', admin_uid, 25)

        new_org_doc = om.assign_users(
            org_doc['_id'],
            ['member1@example.com', 'member2@example.com'])

        db = self.app.db('organizations')
        db_org = db.find_one(org_doc['_id'])

        self.assertEqual([member1_uid], db_org['members'])
        self.assertEqual(['member2@example.com'], db_org['unknown_members'])

        self.assertEqual([member1_uid], new_org_doc['members'])
        self.assertEqual(['member2@example.com'], new_org_doc['unknown_members'])

    def test_remove_users(self):
        self.enter_app_context()
        om = self.app.org_manager

        admin_uid = self.create_user(24 * 'a')
        self.create_user(24 * 'b', email='member1@example.com')
        org_doc = om.create_new_org('Хакеры', admin_uid, 25)

        om.assign_users(
            org_doc['_id'],
            ['member1@example.com', 'member2@example.com'])

        new_org_doc = None  # to prevent 'might not be assigned' warning later on.
        for email in ('member1@example.com', 'member2@example.com'):
            new_org_doc = om.remove_user(org_doc['_id'], email=email)

        db = self.app.db('organizations')
        db_org = db.find_one(org_doc['_id'])

        self.assertEqual([], db_org['members'])
        self.assertEqual([], db_org['unknown_members'])

        self.assertEqual([], new_org_doc['members'])
        self.assertEqual([], new_org_doc['unknown_members'])

    def test_assign_user_roles(self):
        self.enter_app_context()

        admin_uid = self.create_user(24 * 'a')
        member1_uid = self.create_user(24 * 'b',
                                       email='member1@example.com',
                                       roles={'subscriber', 'monkeyhead'})
        om = self.app.org_manager
        org_doc = om.create_new_org('Хакеры', admin_uid, 25,
                                    org_roles=['org-xакеры'])

        new_org_doc = om.assign_users(org_doc['_id'], ['member1@example.com'])
        self.assertEqual(['org-xакеры'], new_org_doc['org_roles'])

        users_coll = self.app.db('users')

        member1_doc = users_coll.find_one(member1_uid)
        self.assertEqual(set(member1_doc['roles']), {'subscriber', 'monkeyhead', 'org-xакеры'})

    def test_revoke_user_roles_simple(self):
        self.enter_app_context()

        admin_uid = self.create_user(24 * 'a')
        member1_uid = self.create_user(24 * 'b',
                                       email='member1@example.com',
                                       roles={'subscriber', 'monkeyhead'})
        om = self.app.org_manager
        org_doc = om.create_new_org('Хакеры', admin_uid, 25, org_roles=['org-xакеры'])

        om.assign_users(org_doc['_id'], ['member1@example.com'])
        om.remove_user(org_doc['_id'], email='member1@example.com')

        users_coll = self.app.db('users')

        member1_doc = users_coll.find_one(member1_uid)
        self.assertEqual(set(member1_doc['roles']), {'subscriber', 'monkeyhead'})

    def test_revoke_user_roles_multiorg_by_email(self):
        self.enter_app_context()

        admin_uid = self.create_user(24 * 'a')
        member1_uid = self.create_user(24 * 'b',
                                       email='member1@example.com',
                                       roles={'subscriber', 'monkeyhead'})
        om = self.app.org_manager
        org1 = om.create_new_org('Хакеры', admin_uid, 25, org_roles=['org-xакеры', 'org-subs'])
        org2 = om.create_new_org('अजिङ्गर', admin_uid, 25, org_roles=['org-अजिङ्गर', 'org-subs'])

        om.assign_users(org1['_id'], ['member1@example.com'])
        om.assign_users(org2['_id'], ['member1@example.com'])
        om.remove_user(org1['_id'], email='member1@example.com')

        users_coll = self.app.db('users')

        member1_doc = users_coll.find_one(member1_uid)
        self.assertEqual(set(member1_doc['roles']),
                         {'subscriber', 'monkeyhead', 'org-subs', 'org-अजिङ्गर'})

    def test_revoke_user_roles_multiorg_by_user_id(self):
        self.enter_app_context()

        admin_uid = self.create_user(24 * 'a')
        member1_uid = self.create_user(24 * 'b',
                                       email='member1@example.com',
                                       roles={'subscriber', 'monkeyhead'})
        om = self.app.org_manager
        org1 = om.create_new_org('Хакеры', admin_uid, 25, org_roles=['org-xакеры', 'org-subs'])
        org2 = om.create_new_org('अजिङ्गर', admin_uid, 25, org_roles=['org-अजिङ्गर', 'org-subs'])

        # Hack the DB to add the member as "unknown member" too, even though we know this user.
        # This has to be handled cleanly by the removal too.
        orgs_coll = self.app.db('organizations')
        orgs_coll.update_one({'_id': org1['_id']},
                             {'$set': {'unknown_members': ['member1@example.com']}})

        om.assign_users(org1['_id'], ['member1@example.com'])
        om.assign_users(org2['_id'], ['member1@example.com'])
        om.remove_user(org1['_id'], user_id=member1_uid)

        users_coll = self.app.db('users')

        member1_doc = users_coll.find_one(member1_uid)
        self.assertEqual(set(member1_doc['roles']),
                         {'subscriber', 'monkeyhead', 'org-subs', 'org-अजिङ्गर'})

        # The unknown members list should be empty.
        db_org1 = orgs_coll.find_one(org1['_id'])
        self.assertEqual(db_org1['unknown_members'], [])


class OrganizationPatchTest(AbstractPillarTest):
    """Test PATCHing organizations."""

    def test_assign_users(self):
        self.enter_app_context()

        admin_uid = self.create_user(24 * 'a', token='admin-token')
        member1_uid = self.create_user(24 * 'b', email='member1@example.com')

        om = self.app.org_manager
        org_doc = om.create_new_org('Хакеры', admin_uid, 25)
        org_id = org_doc['_id']

        # Try the PATCH
        resp = self.patch(f'/api/organizations/{org_id}',
                          json={
                              'op': 'assign-users',
                              'emails': ['member1@example.com', 'member2@example.com'],
                          },
                          auth_token='admin-token')
        new_org_doc = resp.get_json()

        db = self.app.db('organizations')
        db_org = db.find_one(org_id)

        self.assertEqual([member1_uid], db_org['members'])
        self.assertEqual(['member2@example.com'], db_org['unknown_members'])

        self.assertEqual([str(member1_uid)], new_org_doc['members'])
        self.assertEqual(['member2@example.com'], new_org_doc['unknown_members'])

    def test_assign_users_access_denied(self):
        self.enter_app_context()

        admin_uid = self.create_user(24 * 'a', token='admin-token')
        self.create_user(24 * 'b', email='member1@example.com', token='monkey-token')

        om = self.app.org_manager
        org_doc = om.create_new_org('Хакеры', admin_uid, 25)
        org_id = org_doc['_id']

        # Try the PATCH
        self.patch(f'/api/organizations/{org_id}',
                   json={
                       'op': 'assign-users',
                       'emails': ['member1@example.com', 'member2@example.com'],
                   },
                   auth_token='monkey-token',
                   expected_status=403)

        db = self.app.db('organizations')
        db_org = db.find_one(org_id)

        self.assertEqual([], db_org['members'])
        self.assertEqual([], db_org['unknown_members'])

    def test_remove_user_by_email(self):
        self.enter_app_context()
        om = self.app.org_manager

        admin_uid = self.create_user(24 * 'a', token='admin-token')
        self.create_user(24 * 'b', email='member1@example.com')
        org_doc = om.create_new_org('Хакеры', admin_uid, 25)
        org_id = org_doc['_id']

        om.assign_users(org_id, ['member1@example.com', 'member2@example.com'])

        # Try the PATCH to remove a known user
        resp = self.patch(f'/api/organizations/{org_id}',
                          json={
                              'op': 'remove-user',
                              'email': 'member1@example.com',
                          },
                          auth_token='admin-token')
        new_org_doc = resp.get_json()

        db = self.app.db('organizations')
        db_org = db.find_one(org_id)

        self.assertEqual([], db_org['members'])
        self.assertEqual(['member2@example.com'], db_org['unknown_members'])

        self.assertEqual([], new_org_doc['members'])
        self.assertEqual(['member2@example.com'], new_org_doc['unknown_members'])

        # Try the PATCH to remove an unknown user
        resp = self.patch(f'/api/organizations/{org_id}',
                          json={
                              'op': 'remove-user',
                              'email': 'member2@example.com',
                          },
                          auth_token='admin-token')
        new_org_doc = resp.get_json()

        db_org = db.find_one(org_id)

        self.assertEqual([], db_org['members'])
        self.assertEqual([], db_org['unknown_members'])

        self.assertEqual([], new_org_doc['members'])
        self.assertEqual([], new_org_doc['unknown_members'])

    def test_remove_user_by_id(self):
        self.enter_app_context()
        om = self.app.org_manager

        admin_uid = self.create_user(24 * 'a', token='admin-token')
        member_uid = self.create_user(24 * 'b', email='member1@example.com')
        org_doc = om.create_new_org('Хакеры', admin_uid, 25)
        org_id = org_doc['_id']

        om.assign_users(org_id, ['member1@example.com', 'member2@example.com'])

        # Try the PATCH to remove a known user
        resp = self.patch(f'/api/organizations/{org_id}',
                          json={
                              'op': 'remove-user',
                              'user_id': str(member_uid),
                          },
                          auth_token='admin-token')
        new_org_doc = resp.get_json()

        db = self.app.db('organizations')
        db_org = db.find_one(org_id)

        self.assertEqual([], db_org['members'])
        self.assertEqual(['member2@example.com'], db_org['unknown_members'])

        self.assertEqual([], new_org_doc['members'])
        self.assertEqual(['member2@example.com'], new_org_doc['unknown_members'])

        # Try the PATCH to remove an unknown user
        resp = self.patch(f'/api/organizations/{org_id}',
                          json={
                              'op': 'remove-user',
                              'user_id': 24 * 'f',
                          },
                          auth_token='admin-token',
                          expected_status=422)

        db_org = db.find_one(org_id)
        self.assertEqual([], db_org['members'])
        self.assertEqual(['member2@example.com'], db_org['unknown_members'])

    def test_edit_from_web(self):
        self.enter_app_context()
        om = self.app.org_manager

        admin_uid = self.create_user(24 * 'a', token='admin-token')
        org_doc = om.create_new_org('Хакеры', admin_uid, 25)
        org_id = org_doc['_id']

        # Try the PATCH to remove a known user
        self.patch(f'/api/organizations/{org_id}',
                   json={
                       'op': 'edit-from-web',
                       'name': '  Blender Institute ',
                       'description': '\nOpen Source animation studio ',
                       'website': '   https://blender.institute/  ',
                   },
                   auth_token='admin-token',
                   expected_status=204)

        db = self.app.db('organizations')
        db_org = db.find_one(org_id)

        self.assertEqual('Blender Institute', db_org['name'])
        self.assertEqual('Open Source animation studio', db_org['description'])
        self.assertEqual('https://blender.institute/', db_org['website'])
