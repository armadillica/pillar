# -*- encoding: utf-8 -*-

from __future__ import absolute_import
import datetime

from bson import tz_util, ObjectId

from pillar.tests import AbstractPillarTest
from pillar.tests import common_test_data as ctd
from pillar.api.projects.utils import get_node_type

EXAMPLE_PROJECT_OLD_ATTACHMENT_SCHEMA_ID = ObjectId('5673541534134154134513c3')
EXAMPLE_PROJECT_OLD_ATTACHMENT_SCHEMA = {
    u'_created': datetime.datetime(2015, 12, 17, 13, 22, 56, tzinfo=tz_util.utc),
    u'_etag': u'cc4643e98d3606f87bbfaaa200bfbae941b642f3',
    u'_id': EXAMPLE_PROJECT_OLD_ATTACHMENT_SCHEMA_ID,
    u'_updated': datetime.datetime(2016, 1, 7, 18, 59, 4, tzinfo=tz_util.utc),
    u'category': u'assets',
    u'description': u'Welcome to this curated collection of Blender Institute textures and image '
                    u'resources. This collection is an on-going project, as with each project we '
                    u'create a number of textures based on our own resources (photographs, scans, '
                    u'etc.) or made completely from scratch. At the moment you can find all the '
                    u'textures from the past Open Projects that were deemed re-usable. \r\n\r\n'
                    u'People who have contributed to these textures:\r\n\r\nAndrea Weikert, Andy '
                    u'Goralczyk, Basse Salmela, Ben Dansie, Campbell Barton, Enrico Valenza, Ian '
                    u'Hubert, Kjartan Tysdal, Manu J\xe4rvinen, Massimiliana Pulieso, Matt Ebb, '
                    u'Pablo Vazquez, Rob Tuytel, Roland Hess, Sarah Feldlaufer, S\xf6nke M\xe4ter',
    u'is_private': False,
    u'name': u'Unittest project',
    u'node_types': [
        {u'description': u'Group for texture node type',
         u'dyn_schema': {u'order': {u'type': u'integer'},
                         u'status': {u'allowed': [u'published', u'pending'],
                                     u'type': u'string'},
                         u'url': {u'type': u'string'}},
         u'form_schema': {},
         u'name': u'group_texture',
         u'parent': [u'group_texture', u'project']},
        {u'description': u'Folder node',
         u'dyn_schema': {u'notes': {u'maxlength': 256, u'type': u'string'},
                         u'order': {u'type': u'integer'},
                         u'status': {u'allowed': [u'published', u'pending'],
                                     u'type': u'string'},
                         u'url': {u'type': u'string'}},
         u'form_schema': {},
         u'name': u'group',
         u'parent': [u'group', u'project']},
        {u'description': u'Basic Asset Type',
         u'dyn_schema': {
             u'attachments': {u'schema': {u'schema': {u'field': {u'type': u'string'},
                                                      u'files': {u'schema': {
                                                          u'schema': {u'file': {
                                                              u'data_relation': {
                                                                  u'embeddable': True,
                                                                  u'field': u'_id',
                                                                  u'resource': u'files'},
                                                              u'type': u'objectid'},
                                                              u'size': {
                                                                  u'type': u'string'},
                                                              u'slug': {
                                                                  u'minlength': 1,
                                                                  u'type': u'string'}},
                                                          u'type': u'dict'},
                                                          u'type': u'list'}},
                                          u'type': u'dict'},
                              u'type': u'list'},
             u'categories': {u'type': u'string'},
             u'content_type': {u'type': u'string'},
             u'file': {u'data_relation': {u'embeddable': True,
                                          u'field': u'_id',
                                          u'resource': u'files'},
                       u'type': u'objectid'},
             u'order': {u'type': u'integer'},
             u'status': {u'allowed': [u'published',
                                      u'pending',
                                      u'processing'],
                         u'type': u'string'},
             u'tags': {u'schema': {u'type': u'string'}, u'type': u'list'}},
         u'form_schema': {u'attachments': {u'visible': False},
                          u'content_type': {u'visible': False},
                          u'file': {u'visible': False}},
         u'name': u'asset',
         u'parent': [u'group']},
        {u'description': u'Entrypoint to a remote or local storage solution',
         u'dyn_schema': {u'backend': {u'type': u'string'},
                         u'subdir': {u'type': u'string'}},
         u'form_schema': {u'backend': {}, u'subdir': {}},
         u'name': u'storage',
         u'parent': [u'group', u'project'],
         u'permissions': {u'groups': [{u'group': ctd.EXAMPLE_ADMIN_GROUP_ID,
                                       u'methods': [u'GET', u'PUT', u'POST']},
                                      {u'group': ctd.EXAMPLE_PROJECT_READONLY_GROUP_ID,
                                       u'methods': [u'GET']},
                                      {u'group': ctd.EXAMPLE_PROJECT_READONLY_GROUP2_ID,
                                       u'methods': [u'GET']}],
                          u'users': [],
                          u'world': []}},
        {u'description': u'Comments for asset nodes, pages, etc.',
         u'dyn_schema': {u'confidence': {u'type': u'float'},
                         u'content': {u'minlength': 5, u'type': u'string'},
                         u'is_reply': {u'type': u'boolean'},
                         u'rating_negative': {u'type': u'integer'},
                         u'rating_positive': {u'type': u'integer'},
                         u'ratings': {u'schema': {
                             u'schema': {u'is_positive': {u'type': u'boolean'},
                                         u'user': {u'type': u'objectid'},
                                         u'weight': {u'type': u'integer'}},
                             u'type': u'dict'},
                             u'type': u'list'},
                         u'status': {u'allowed': [u'published', u'flagged', u'edited'],
                                     u'type': u'string'}},
         u'form_schema': {},
         u'name': u'comment',
         u'parent': [u'asset', u'comment']},
        {u'description': u'Container for node_type post.',
         u'dyn_schema': {u'categories': {u'schema': {u'type': u'string'},
                                         u'type': u'list'},
                         u'template': {u'type': u'string'}},
         u'form_schema': {},
         u'name': u'blog',
         u'parent': [u'project']},
        {u'description': u'A blog post, for any project',
         u'dyn_schema': {
             u'attachments': {u'schema': {u'schema': {u'field': {u'type': u'string'},
                                                      u'files': {u'schema': {
                                                          u'schema': {u'file': {
                                                              u'data_relation': {
                                                                  u'embeddable': True,
                                                                  u'field': u'_id',
                                                                  u'resource': u'files'},
                                                              u'type': u'objectid'},
                                                              u'size': {
                                                                  u'type': u'string'},
                                                              u'slug': {
                                                                  u'minlength': 1,
                                                                  u'type': u'string'}},
                                                          u'type': u'dict'},
                                                          u'type': u'list'}},
                                          u'type': u'dict'},
                              u'type': u'list'},
             u'category': {u'type': u'string'},
             u'content': {u'maxlength': 90000,
                          u'minlength': 5,
                          u'required': True,
                          u'type': u'string'},
             u'status': {u'allowed': [u'published', u'pending'],
                         u'default': u'pending',
                         u'type': u'string'},
             u'url': {u'type': u'string'}},
         u'form_schema': {u'attachments': {u'visible': False}},
         u'name': u'post',
         u'parent': [u'blog']},
        {u'description': u'Image Texture',
         u'dyn_schema': {u'aspect_ratio': {u'type': u'float'},
                         u'categories': {u'type': u'string'},
                         u'files': {u'schema': {u'schema': {
                             u'file': {u'data_relation': {u'embeddable': True,
                                                          u'field': u'_id',
                                                          u'resource': u'files'},
                                       u'type': u'objectid'},
                             u'is_tileable': {u'type': u'boolean'},
                             u'map_type': {u'allowed': [u'color',
                                                        u'specular',
                                                        u'bump',
                                                        u'normal',
                                                        u'translucency',
                                                        u'emission',
                                                        u'alpha'],
                                           u'type': u'string'}},
                             u'type': u'dict'},
                             u'type': u'list'},
                         u'is_landscape': {u'type': u'boolean'},
                         u'is_tileable': {u'type': u'boolean'},
                         u'order': {u'type': u'integer'},
                         u'resolution': {u'type': u'string'},
                         u'status': {u'allowed': [u'published',
                                                  u'pending',
                                                  u'processing'],
                                     u'type': u'string'},
                         u'tags': {u'schema': {u'type': u'string'}, u'type': u'list'}},
         u'form_schema': {u'content_type': {u'visible': False},
                          u'files': {u'visible': False}},
         u'name': u'texture',
         u'parent': [u'group']}],
    u'nodes_blog': [],
    u'nodes_featured': [],
    u'nodes_latest': [],
    u'permissions': {u'groups': [{u'group': ctd.EXAMPLE_ADMIN_GROUP_ID,
                                  u'methods': [u'GET', u'POST', u'PUT', u'DELETE']}],
                     u'users': [],
                     u'world': [u'GET']},
    u'status': u'published',
    u'summary': u'Texture collection from all Blender Institute open projects.',
    u'url': u'attachment-schema-update',
    u'picture_header': ObjectId('5673f260c379cf0007b31bc4'),
    u'picture_square': ObjectId('5673f256c379cf0007b31bc3'),
    u'user': ctd.EXAMPLE_PROJECT_OWNER_ID}

EXAMPLE_ASSET_NODE_OLD_ATTACHMENT_SCHEMA = {
    u'_id': ObjectId('572761099837730efe8e120d'),
    u'picture': ObjectId('5673f260c379cf0007b31bc4'),
    u'description': u'',
    u'node_type': u'asset',
    u'user': ctd.EXAMPLE_PROJECT_OWNER_ID,
    u'properties': {
        u'status': u'published',
        u'content_type': u'image',
        u'file': ObjectId('5673f260c379cf0007b31bed'),
        u'attachments': [{
            'files': [
                {'slug': '01', 'file': ObjectId('5679b25ec379cf25636688f6')},
                {'slug': '02b', 'file': ObjectId('5679b308c379cf25636688f7')},
                {'slug': '03', 'file': ObjectId('5679b33bc379cf25636688f8')},
            ],
            'field': 'properties.content'
        }],
    },
    u'_updated': datetime.datetime(2016, 5, 2, 14, 19, 58, 0, tzinfo=tz_util.utc),
    u'name': u'Image test',
    u'project': EXAMPLE_PROJECT_OLD_ATTACHMENT_SCHEMA_ID,
    u'_created': datetime.datetime(2016, 5, 2, 14, 19, 37, 0, tzinfo=tz_util.utc),
    u'_etag': u'6b8589b42c880e3626f43f3e82a5c5b946742687'
}

EXAMPLE_PAGE_NODE_OLD_ATTACHMENT_SCHEMA = {
    u'_id': ObjectId('572761099837730efe8e120a'),
    u'picture': ObjectId('5673f260c379cf0007b31bc4'),
    u'description': u'',
    u'node_type': u'page',
    u'user': ctd.EXAMPLE_PROJECT_OWNER_ID,
    u'properties': {
        u'status': u'published',
        u'content': u'Überinteressant Verhaaltje™ voor het slapengaan.',
        u'url': u'jemoeder',
        u'attachments': [{
            'files': [
                {'slug': '03', 'file': ObjectId('5679b33bc379cf256366ddd8')},
                {'slug': '04', 'file': ObjectId('5679b35bc379cf256366ddd9')},
            ],
            'field': 'properties.content'
        }],
    },
    u'_updated': datetime.datetime(2016, 5, 2, 14, 19, 58, 0, tzinfo=tz_util.utc),
    u'name': u'Page test',
    u'project': EXAMPLE_PROJECT_OLD_ATTACHMENT_SCHEMA_ID,
    u'_created': datetime.datetime(2016, 5, 2, 14, 19, 37, 0, tzinfo=tz_util.utc),
    u'_etag': u'6b8589b42c880e3626f43f3e82a5c5b946742687'
}


class AbstractNodeReplacementTest(AbstractPillarTest):
    project_overrides = None

    def setUp(self, **kwargs):
        AbstractPillarTest.setUp(self, **kwargs)

        self.project_id, self.proj = self.ensure_project_exists(
            project_overrides=self.project_overrides)

        self.ensure_file_exists({
            '_id': EXAMPLE_PROJECT_OLD_ATTACHMENT_SCHEMA[u'picture_header'],
            'project': EXAMPLE_PROJECT_OLD_ATTACHMENT_SCHEMA_ID,
        })
        self.ensure_file_exists({
            '_id': EXAMPLE_PROJECT_OLD_ATTACHMENT_SCHEMA[u'picture_square'],
            'project': EXAMPLE_PROJECT_OLD_ATTACHMENT_SCHEMA_ID,
        })

    def fetch_project_from_db(self):
        return super(AbstractNodeReplacementTest, self).fetch_project_from_db(self.project_id)

    def add_group_permission_to_asset_node_type(self):
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

        return group_perms


class ReplaceNodeTypesTest(AbstractNodeReplacementTest):
    def test_replace_pillar_node_type_schemas(self):
        from pillar.api.node_types.group import node_type_group
        from pillar.cli import replace_pillar_node_type_schemas

        group_perms = self.add_group_permission_to_asset_node_type()

        # Run the CLI command
        with self.app.test_request_context():
            replace_pillar_node_type_schemas(proj_url=self.proj['url'])

        # Fetch the project again from MongoDB
        dbproj = self.fetch_project_from_db()

        # Test that the node types were updated
        nt_group = get_node_type(dbproj, 'group')
        self.assertEqual(node_type_group['description'], nt_group['description'])

        # Test that the permissions set previously are still there.
        nt_asset = get_node_type(dbproj, 'asset')
        self.assertEqual([group_perms], nt_asset['permissions']['groups'])


class UpgradeAttachmentSchemaTest(AbstractNodeReplacementTest):
    project_overrides = EXAMPLE_PROJECT_OLD_ATTACHMENT_SCHEMA

    def setUp(self, **kwargs):
        super(UpgradeAttachmentSchemaTest, self).setUp(**kwargs)

        self.ensure_file_exists(
            {'_id': EXAMPLE_ASSET_NODE_OLD_ATTACHMENT_SCHEMA[u'properties'][u'file']})

        for node in (EXAMPLE_ASSET_NODE_OLD_ATTACHMENT_SCHEMA,
                     EXAMPLE_PAGE_NODE_OLD_ATTACHMENT_SCHEMA):
            for att in node[u'properties'][u'attachments']:
                for filedict in att[u'files']:
                    self.ensure_file_exists({'_id': filedict[u'file']})

    def test_schema_upgrade(self):
        from pillar.cli import upgrade_attachment_schema
        from pillar.api.node_types.asset import node_type_asset

        group_perms = self.add_group_permission_to_asset_node_type()

        with self.app.test_request_context():
            upgrade_attachment_schema(self.proj['url'])

        dbproj = self.fetch_project_from_db()

        # Test that the schemas were upgraded to the current schema.
        nt_asset = get_node_type(dbproj, 'asset')
        self.assertEqual(node_type_asset['dyn_schema']['attachments'],
                         nt_asset['dyn_schema']['attachments'])

        # Test that the permissions set previously are still there.
        self.assertEqual([group_perms], nt_asset['permissions']['groups'])


class CreateBlogTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        AbstractPillarTest.setUp(self, **kwargs)

        self.project_id, self.proj = self.ensure_project_exists()
        self.ensure_file_exists({'_id': self.proj[u'picture_header']})
        self.ensure_file_exists({'_id': self.proj[u'picture_square']})

    def test_create_blog(self):
        """Very simple test to check the create_blog CLI command."""

        from pillar.cli import create_blog

        with self.app.test_request_context():
            create_blog(self.proj['url'])

        dbproj = self.fetch_project_from_db()
        nt_blog = get_node_type(dbproj, 'blog')
        self.assertIsNotNone(nt_blog)

        # I trust that the blog node has been created too.
