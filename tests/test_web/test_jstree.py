from unittest import mock

from bson import ObjectId
from dateutil.parser import parse
from flask import Markup

from pillarsdk import Node
from pillar.tests import AbstractPillarTest


class JSTreeTest(AbstractPillarTest):
    def test_jstree_parse_node(self):
        from pillar.web.utils.jstree import jstree_parse_node

        node_doc = {'_id': ObjectId('55f338f92beb3300c4ff99fe'),
                    '_created': parse('2015-09-11T22:26:33.000+0200'),
                    '_updated': parse('2015-10-30T22:44:27.000+0100'),
                    '_etag': '5248485b4ea7e55e858ff84b1bd4aae88917a37c',
                    'picture': ObjectId('55f338f92beb3300c4ff99de'),
                    'description': 'Play the full movie and see how it was cobbled together.',
                    'parent': ObjectId('55f338f92beb3300c4ff99f9'),
                    'project': ObjectId('55f338f92beb3300c4ff99e5'),
                    'node_type': 'asset',
                    'user': ObjectId('552b066b41acdf5dec4436f2'),
                    'properties': {'status': 'published',
                                   'file': ObjectId('55f338f92beb3300c4ff99c2'),
                                   'content_type': 'file'},
                    'name': 'Live <strong>Edit</strong>'}

        # Mocking url_for_node prevents us from setting up a project and an URLer service.
        with mock.patch('pillar.web.nodes.routes.url_for_node') as mock_url_for_node:
            mock_url_for_node.return_value = '/the/url'
            parsed = jstree_parse_node(Node(node_doc))

        self.assertEqual(parsed, {
            'id': 'n_55f338f92beb3300c4ff99fe',
            'a_attr': {'href': '/the/url'},
            'li_attr': {'data-node-type': 'asset'},
            'text': Markup('Live &lt;strong&gt;Edit&lt;/strong&gt;'),
            'type': 'file',
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
                    'project': ObjectId('55f338f92beb3300c4ff99e5'),
                    'node_type': 'blog',
                    'user': ObjectId('552b066b41acdf5dec4436f2'),
                    'properties': {'status': 'published',
                                   'file': ObjectId('55f338f92beb3300c4ff99c2'),
                                   'content_type': 'file'},
                    'name': 'Live <strong>Edit</strong>'}

        # Mocking url_for_node prevents us from setting up a project and an URLer service.
        with mock.patch('pillar.web.nodes.routes.url_for_node') as mock_url_for_node:
            mock_url_for_node.return_value = '/the/url'
            parsed = jstree_parse_node(Node(node_doc))

        self.assertEqual(parsed, {
            'id': 'n_55f338f92beb3300c4ff99fe',
            'a_attr': {'href': '/the/url'},
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
                    'project': ObjectId('55f338f92beb3300c4ff99e5'),
                    'node_type': 'asset',
                    'user': ObjectId('552b066b41acdf5dec4436f2'),
                    'name': 'Live <strong>Edit</strong>'}

        # Mocking url_for_node prevents us from setting up a project and an URLer service.
        with mock.patch('pillar.web.nodes.routes.url_for_node') as mock_url_for_node:
            mock_url_for_node.return_value = '/the/url'
            parsed = jstree_parse_node(Node(node_doc))

        self.assertEqual(parsed, {
            'id': 'n_55f338f92beb3300c4ff99fe',
            'a_attr': {'href': '/the/url'},
            'li_attr': {'data-node-type': 'asset'},
            'text': Markup('Live &lt;strong&gt;Edit&lt;/strong&gt;'),
            'type': 'asset',
            'children': False,
            'custom_view': False,
        })
