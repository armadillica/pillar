import copy

from pillar.tests import AbstractPillarTest
from pillar.tests import common_test_data as ctd


class CoerceMarkdownTest(AbstractPillarTest):
    def test_node_description(self):
        from pillar.markdown import markdown
        pid, uid = self.create_project_with_admin(24 * 'a')
        self.create_valid_auth_token(uid, 'token-a')
        node = {
            'node_type': 'group',
            'name': 'Test group',
            'description': '# Title\n\nThis is content.',
            'properties': {},
            'project': pid,
            'user': uid,
        }

        created_data = self.post('/api/nodes', json=node, expected_status=201,
                                 auth_token='token-a').json()
        node_id = created_data['_id']

        json_node = self.get(f'/api/nodes/{node_id}', auth_token='token-a').json()
        self.assertEqual(markdown(node['description']), json_node['_description_html'])

    def test_project_description(self):
        from pillar.markdown import markdown
        from pillar.api.utils import remove_private_keys

        uid = self.create_user(24 * 'a', token='token-a')

        # Go through Eve to create the project.
        proj = {
            **ctd.EXAMPLE_PROJECT,
            'description': '# Title\n\nThis is content.',
            'user': uid,
        }
        proj.pop('picture_header')
        proj.pop('picture_square')
        proj.pop('permissions')

        r, _, _, status = self.app.post_internal('projects', remove_private_keys(proj))
        self.assertEqual(201, status, f'failed because {r}')

        pid = r['_id']

        json_proj = self.get(f'/api/projects/{pid}', auth_token='token-a').json()
        json_proj.pop('node_types', None)  # just to make it easier to print
        import pprint
        pprint.pprint(json_proj)
        self.assertEqual(markdown(proj['description']), json_proj['_description_html'])
