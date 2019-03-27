from bson import ObjectId
from dateutil.parser import parse
from flask import Markup

from pillarsdk import Node
from pillar.tests import AbstractPillarTest


class JSTreeTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        super().setUp(**kwargs)
        self.project_id, self.project = self.ensure_project_exists()

    def test_jstree_parse_node(self):
        from pillar.web.utils.jstree import jstree_parse_node

        node_doc = {'_id': ObjectId('55f338f92beb3300c4ff99fe'),
                    '_created': parse('2015-09-11T22:26:33.000+0200'),
                    '_updated': parse('2015-10-30T22:44:27.000+0100'),
                    '_etag': '5248485b4ea7e55e858ff84b1bd4aae88917a37c',
                    'picture': ObjectId('55f338f92beb3300c4ff99de'),
                    'description': 'Play the full movie and see how it was cobbled together.',
                    'parent': ObjectId('55f338f92beb3300c4ff99f9'),
                    'project': self.project_id,
                    'node_type': 'asset',
                    'user': ObjectId('552b066b41acdf5dec4436f2'),
                    'properties': {'status': 'published',
                                   'file': ObjectId('55f338f92beb3300c4ff99c2'),
                                   'content_type': 'file'},
                    'name': 'Live <strong>Edit</strong>'}

        with self.app.test_request_context():
            parsed = jstree_parse_node(Node(node_doc))

        self.assertEqual(parsed, {
            'id': 'n_55f338f92beb3300c4ff99fe',
            'a_attr': {'href': f"/p/{self.project['url']}/55f338f92beb3300c4ff99fe"},
            'li_attr': {'data-node-type': 'asset'},
            'text': Markup('Live &lt;strong&gt;Edit&lt;/strong&gt;'),
            'type': 'file',
            'children': False,
            'custom_view': False,
        })

    def test_jstree_parse_video_node(self):
        from pillar.web.utils.jstree import jstree_parse_node

        node_doc = {'_id': ObjectId('55f338f92beb3300c4ff99fe'),
                    '_created': parse('2015-09-11T22:26:33.000+0200'),
                    '_updated': parse('2015-10-30T22:44:27.000+0100'),
                    '_etag': '5248485b4ea7e55e858ff84b1bd4aae88917a37c',
                    'picture': ObjectId('55f338f92beb3300c4ff99de'),
                    'description': 'Play the full movie and see how it was cobbled together.',
                    'parent': ObjectId('55f338f92beb3300c4ff99f9'),
                    'project': self.project_id,
                    'node_type': 'asset',
                    'user': ObjectId('552b066b41acdf5dec4436f2'),
                    'properties': {'status': 'published',
                                   'file': ObjectId('55f338f92beb3300c4ff99c2'),
                                   'content_type': 'video',
                                   },
                    'name': 'Live <strong>Edit</strong>'}

        with self.app.test_request_context():
            parsed = jstree_parse_node(Node(node_doc))

        self.assertEqual(parsed, {
            'id': 'n_55f338f92beb3300c4ff99fe',
            'a_attr': {'href': f"/p/{self.project['url']}/55f338f92beb3300c4ff99fe"},
            'li_attr': {'data-node-type': 'asset'},
            'text': Markup('Live &lt;strong&gt;Edit&lt;/strong&gt;'),
            'type': 'video',
            'children': False,
            'custom_view': False,
        })

    def test_jstree_parse_blog_node(self):
        from pillar.web.utils.jstree import jstree_parse_node

        node_doc = {'_id': ObjectId('55f338f92beb3300c4ff99fe'),
                    '_created': parse('2015-09-11T22:26:33.000+0200'),
                    '_updated': parse('2015-10-30T22:44:27.000+0100'),
                    '_etag': '5248485b4ea7e55e858ff84b1bd4aae88917a37c',
                    'picture': ObjectId('55f338f92beb3300c4ff99de'),
                    'description': 'Play the full movie and see how it was cobbled together.',
                    'parent': ObjectId('55f338f92beb3300c4ff99f9'),
                    'project': self.project_id,
                    'node_type': 'blog',
                    'user': ObjectId('552b066b41acdf5dec4436f2'),
                    'properties': {'status': 'published',
                                   'file': ObjectId('55f338f92beb3300c4ff99c2'),
                                   'content_type': 'file'},
                    'name': 'Live <strong>Edit</strong>'}

        with self.app.test_request_context():
            parsed = jstree_parse_node(Node(node_doc))

        self.assertEqual(parsed, {
            'id': 'n_55f338f92beb3300c4ff99fe',
            'a_attr': {'href': '/blog/'},
            'li_attr': {'data-node-type': 'blog'},
            'text': Markup('Live &lt;strong&gt;Edit&lt;/strong&gt;'),
            'type': 'blog',
            'children': False,
            'custom_view': True,
        })

    def test_jstree_parse_just_created_node(self):
        from pillar.web.utils.jstree import jstree_parse_node

        node_doc = {'_id': ObjectId('55f338f92beb3300c4ff99fe'),
                    '_created': parse('2015-09-11T22:26:33.000+0200'),
                    '_updated': parse('2015-10-30T22:44:27.000+0100'),
                    '_etag': '5248485b4ea7e55e858ff84b1bd4aae88917a37c',
                    'project': self.project_id,
                    'node_type': 'asset',
                    'user': ObjectId('552b066b41acdf5dec4436f2'),
                    'name': 'Live <strong>Edit</strong>'}

        with self.app.test_request_context():
            parsed = jstree_parse_node(Node(node_doc))

        self.assertEqual(parsed, {
            'id': 'n_55f338f92beb3300c4ff99fe',
            'a_attr': {'href': f"/p/{self.project['url']}/55f338f92beb3300c4ff99fe"},
            'li_attr': {'data-node-type': 'asset'},
            'text': Markup('Live &lt;strong&gt;Edit&lt;/strong&gt;'),
            'type': 'asset',
            'children': False,
            'custom_view': False,
        })

    def test_jstree_canary(self):
        """Test that a project's /jstree URL can be called at all.

        This catches a problem we had with MONGO_QUERY_BLACKLIST.
        """

        resp = self.get(f'/p/{self.project["url"]}/jstree')
        self.assertEqual(200, resp.status_code)
