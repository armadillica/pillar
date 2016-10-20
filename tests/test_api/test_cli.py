from __future__ import absolute_import

from pillar.tests import AbstractPillarTest
from pillar.tests import common_test_data as ctd


class PatchCommentTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        AbstractPillarTest.setUp(self, **kwargs)

        # Create a project that doesn't reference non-existing files, so that
        # Eve can actually PUT it later without validation errors.
        self.project_id, self.proj = self.ensure_project_exists(project_overrides={
            'picture_square': None,
            'picture_header': None,
        })

    def test_replace_pillar_node_type_schemas(self):
        from pillar.api.node_types.group import node_type_group
        from pillar.cli import replace_pillar_node_type_schemas

        group_perms = {u'group': ctd.EXAMPLE_PROJECT_READONLY_GROUP_ID,
                       u'methods': [u'POST', u'PUT']}

        # Assign some permissions to the node types, so we're sure they don't get overwritten.
        with self.app.app_context():
            proj_coll = self.app.db()['projects']
            proj_coll.update_one(
                {'_id': self.project_id,
                 'node_types.name': 'asset'},
                {'$push': {'node_types.$.permissions.groups': group_perms}}
            )

        # Run the CLI command
        with self.app.test_request_context():
            replace_pillar_node_type_schemas(proj_url=self.proj['url'])

        # Fetch the project again from MongoDB
        with self.app.app_context():
            proj_coll = self.app.db()['projects']
            dbproj = proj_coll.find_one(self.project_id)

        # Perform our tests
        def nt(node_type_name):
            found = [nt for nt in dbproj['node_types']
                     if nt['name'] == node_type_name]
            return found[0]

        # Test that the node types were updated
        nt_group = nt('group')
        self.assertEqual(node_type_group['description'], nt_group['description'])

        # Test that the permissions set previously are still there.
        nt_asset = nt('asset')
        self.assertEqual([group_perms], nt_asset['permissions']['groups'])
