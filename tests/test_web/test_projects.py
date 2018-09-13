from bson import ObjectId

from pillar.tests import AbstractPillarTest
from pillar.tests import common_test_data as ctd
from pillar.web import system_util
from pillar.web.projects.routes import project_navigation_links, find_project_or_404


class ProjectTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        super().setUp(**kwargs)

        self.pid, self.project = self.ensure_project_exists()
        self.owner_uid = self.create_user(24 * 'a',
                                          groups=[ctd.EXAMPLE_ADMIN_GROUP_ID],
                                          token='admin-token')

        # Create a Node of type page.
        self.node_id = self.create_node({
            '_id': ObjectId('572761099837730efe8e120d'),
            'description': 'This the about page',
            'node_type': 'page',
            'user': self.owner_uid,
            'properties': {
                'status': 'published',
                'url': 'about',
            },
            'name': 'About',
            'project': self.pid,
        })

        self.user_uid = self.create_user(24 * 'b', groups=[ctd.EXAMPLE_ADMIN_GROUP_ID],
                                         token='user-token')

    def test_project_navigation_links_one_page(self):
        """Test link generation for project navigation."""
        with self.app.test_request_context():
            api = system_util.pillar_api()
            project = find_project_or_404(self.project['url'], api=api)
            navigation_links = project_navigation_links(project, api=api)

            # We expect only one link to be in the list
            links = [{'url': '/p/default-project/about', 'label': 'About'}]
            self.assertListEqual(links, navigation_links)

    def test_project_navigation_links_pages_and_blog(self):
        """Test link generation for a project with two Pages and one Blog."""
        # Add one more page to the project
        self.create_node({
            '_id': ObjectId(),
            'description': 'This the awards page',
            'node_type': 'page',
            'user': self.owner_uid,
            'properties': {
                'status': 'published',
                'url': 'awards',
            },
            'name': 'Awards',
            'project': self.pid,
        })
        # Create a Node of type blog.
        self.create_node({
            '_id': ObjectId(),
            'description': 'This the blog page',
            'node_type': 'blog',
            'user': self.owner_uid,
            'properties': {
                'status': 'published',
            },
            'name': 'Blog',
            'project': self.pid,
        })
        # Create a Node of type asset
        self.create_node({
            '_id': ObjectId(),
            'description': 'This is an asset without file',
            'node_type': 'asset',
            'user': self.owner_uid,
            'properties': {
                'status': 'published',
                'content_type': 'image',
            },
            'name': 'Image test',
            'project': self.pid,
        })

        with self.app.test_request_context():
            api = system_util.pillar_api()
            project = find_project_or_404(self.project['url'], api=api)
            navigation_links = project_navigation_links(project, api=api)
            expected_list = [
                {'url': '/blog/', 'label': 'Blog'},  # Blog is the first element of the list (since it's added first)
                {'url': '/p/default-project/about', 'label': 'About'},
                {'url': '/p/default-project/awards', 'label': 'Awards'}]

            self.assertListEqual(expected_list, navigation_links)

    def test_project_no_navigation_links(self):
        """Test link generation in a project with no Pages or Blog."""
        with self.app.test_request_context():
            # Delete the existing page from the database
            self.app.db('nodes').delete_one({'_id': ObjectId('572761099837730efe8e120d')})
            api = system_util.pillar_api()
            project = find_project_or_404(self.project['url'], api=api)
            navigation_links = project_navigation_links(project, api=api)
            # This should result in an empty list
            self.assertListEqual([], navigation_links)
