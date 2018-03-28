# -*- encoding: utf-8 -*-


import datetime

from bson import tz_util, ObjectId

from pillar.tests import AbstractPillarTest
from pillar.tests import common_test_data as ctd
from pillar.api.projects.utils import get_node_type

EXAMPLE_PROJECT_OLD_ATTACHMENT_SCHEMA_ID = ObjectId('5673541534134154134513c3')
EXAMPLE_PROJECT_OLD_ATTACHMENT_SCHEMA = {
    '_created': datetime.datetime(2015, 12, 17, 13, 22, 56, tzinfo=tz_util.utc),
    '_etag': 'cc4643e98d3606f87bbfaaa200bfbae941b642f3',
    '_id': EXAMPLE_PROJECT_OLD_ATTACHMENT_SCHEMA_ID,
    '_updated': datetime.datetime(2016, 1, 7, 18, 59, 4, tzinfo=tz_util.utc),
    'category': 'assets',
    'description': 'Welcome to this curated collection of Blender Institute textures and image '
                    'resources. This collection is an on-going project, as with each project we '
                    'create a number of textures based on our own resources (photographs, scans, '
                    'etc.) or made completely from scratch. At the moment you can find all the '
                    'textures from the past Open Projects that were deemed re-usable. \r\n\r\n'
                    'People who have contributed to these textures:\r\n\r\nAndrea Weikert, Andy '
                    'Goralczyk, Basse Salmela, Ben Dansie, Campbell Barton, Enrico Valenza, Ian '
                    'Hubert, Kjartan Tysdal, Manu J\xe4rvinen, Massimiliana Pulieso, Matt Ebb, '
                    'Pablo Vazquez, Rob Tuytel, Roland Hess, Sarah Feldlaufer, S\xf6nke M\xe4ter',
    'is_private': False,
    'name': 'Unittest project',
    'node_types': [
        {'description': 'Group for texture node type',
         'dyn_schema': {'order': {'type': 'integer'},
                         'status': {'allowed': ['published', 'pending'],
                                     'type': 'string'},
                         'url': {'type': 'string'}},
         'form_schema': {},
         'name': 'group_texture',
         'parent': ['group_texture', 'project']},
        {'description': 'Folder node',
         'dyn_schema': {'notes': {'maxlength': 256, 'type': 'string'},
                         'order': {'type': 'integer'},
                         'status': {'allowed': ['published', 'pending'],
                                     'type': 'string'},
                         'url': {'type': 'string'}},
         'form_schema': {},
         'name': 'group',
         'parent': ['group', 'project']},
        {'description': 'Basic Asset Type',
         'dyn_schema': {
             'attachments': {'schema': {'schema': {'field': {'type': 'string'},
                                                      'files': {'schema': {
                                                          'schema': {'file': {
                                                              'data_relation': {
                                                                  'embeddable': True,
                                                                  'field': '_id',
                                                                  'resource': 'files'},
                                                              'type': 'objectid'},
                                                              'size': {
                                                                  'type': 'string'},
                                                              'slug': {
                                                                  'minlength': 1,
                                                                  'type': 'string'}},
                                                          'type': 'dict'},
                                                          'type': 'list'}},
                                          'type': 'dict'},
                              'type': 'list'},
             'categories': {'type': 'string'},
             'content_type': {'type': 'string'},
             'file': {'data_relation': {'embeddable': True,
                                          'field': '_id',
                                          'resource': 'files'},
                       'type': 'objectid'},
             'order': {'type': 'integer'},
             'status': {'allowed': ['published',
                                      'pending',
                                      'processing'],
                         'type': 'string'},
             'tags': {'schema': {'type': 'string'}, 'type': 'list'}},
         'form_schema': {'attachments': {'visible': False},
                          'content_type': {'visible': False},
                          'file': {'visible': False}},
         'name': 'asset',
         'parent': ['group']},
        {'description': 'Entrypoint to a remote or local storage solution',
         'dyn_schema': {'backend': {'type': 'string'},
                         'subdir': {'type': 'string'}},
         'form_schema': {'backend': {}, 'subdir': {}},
         'name': 'storage',
         'parent': ['group', 'project'],
         'permissions': {'groups': [{'group': ctd.EXAMPLE_ADMIN_GROUP_ID,
                                       'methods': ['GET', 'PUT', 'POST']},
                                      {'group': ctd.EXAMPLE_PROJECT_READONLY_GROUP_ID,
                                       'methods': ['GET']},
                                      {'group': ctd.EXAMPLE_PROJECT_READONLY_GROUP2_ID,
                                       'methods': ['GET']}],
                          'users': [],
                          'world': []}},
        {'description': 'Comments for asset nodes, pages, etc.',
         'dyn_schema': {'confidence': {'type': 'float'},
                         'content': {'minlength': 5, 'type': 'string'},
                         'is_reply': {'type': 'boolean'},
                         'rating_negative': {'type': 'integer'},
                         'rating_positive': {'type': 'integer'},
                         'ratings': {'schema': {
                             'schema': {'is_positive': {'type': 'boolean'},
                                         'user': {'type': 'objectid'},
                                         'weight': {'type': 'integer'}},
                             'type': 'dict'},
                             'type': 'list'},
                         'status': {'allowed': ['published', 'flagged', 'edited'],
                                     'type': 'string'}},
         'form_schema': {},
         'name': 'comment',
         'parent': ['asset', 'comment']},
        {'description': 'Container for node_type post.',
         'dyn_schema': {'categories': {'schema': {'type': 'string'},
                                         'type': 'list'},
                         'template': {'type': 'string'}},
         'form_schema': {},
         'name': 'blog',
         'parent': ['project']},
        {'description': 'A blog post, for any project',
         'dyn_schema': {
             'attachments': {'schema': {'schema': {'field': {'type': 'string'},
                                                      'files': {'schema': {
                                                          'schema': {'file': {
                                                              'data_relation': {
                                                                  'embeddable': True,
                                                                  'field': '_id',
                                                                  'resource': 'files'},
                                                              'type': 'objectid'},
                                                              'size': {
                                                                  'type': 'string'},
                                                              'slug': {
                                                                  'minlength': 1,
                                                                  'type': 'string'}},
                                                          'type': 'dict'},
                                                          'type': 'list'}},
                                          'type': 'dict'},
                              'type': 'list'},
             'category': {'type': 'string'},
             'content': {'maxlength': 90000,
                          'minlength': 5,
                          'required': True,
                          'type': 'string'},
             'status': {'allowed': ['published', 'pending'],
                         'default': 'pending',
                         'type': 'string'},
             'url': {'type': 'string'}},
         'form_schema': {'attachments': {'visible': False}},
         'name': 'post',
         'parent': ['blog']},
        {'description': 'Image Texture',
         'dyn_schema': {'aspect_ratio': {'type': 'float'},
                         'categories': {'type': 'string'},
                         'files': {'schema': {'schema': {
                             'file': {'data_relation': {'embeddable': True,
                                                          'field': '_id',
                                                          'resource': 'files'},
                                       'type': 'objectid'},
                             'is_tileable': {'type': 'boolean'},
                             'map_type': {'allowed': ['color',
                                                        'specular',
                                                        'bump',
                                                        'normal',
                                                        'translucency',
                                                        'emission',
                                                        'alpha'],
                                           'type': 'string'}},
                             'type': 'dict'},
                             'type': 'list'},
                         'is_landscape': {'type': 'boolean'},
                         'is_tileable': {'type': 'boolean'},
                         'order': {'type': 'integer'},
                         'resolution': {'type': 'string'},
                         'status': {'allowed': ['published',
                                                  'pending',
                                                  'processing'],
                                     'type': 'string'},
                         'tags': {'schema': {'type': 'string'}, 'type': 'list'}},
         'form_schema': {'content_type': {'visible': False},
                          'files': {'visible': False}},
         'name': 'texture',
         'parent': ['group']}],
    'nodes_blog': [],
    'nodes_featured': [],
    'nodes_latest': [],
    'permissions': {'groups': [{'group': ctd.EXAMPLE_ADMIN_GROUP_ID,
                                  'methods': ['GET', 'POST', 'PUT', 'DELETE']}],
                     'users': [],
                     'world': ['GET']},
    'status': 'published',
    'summary': 'Texture collection from all Blender Institute open projects.',
    'url': 'attachment-schema-update',
    'picture_header': ObjectId('5673f260c379cf0007b31bc4'),
    'picture_square': ObjectId('5673f256c379cf0007b31bc3'),
    'user': ctd.EXAMPLE_PROJECT_OWNER_ID}

EXAMPLE_ASSET_NODE_OLD_ATTACHMENT_SCHEMA = {
    '_id': ObjectId('572761099837730efe8e120d'),
    'picture': ObjectId('5673f260c379cf0007b31bc4'),
    'description': '',
    'node_type': 'asset',
    'user': ctd.EXAMPLE_PROJECT_OWNER_ID,
    'properties': {
        'status': 'published',
        'content_type': 'image',
        'file': ObjectId('5673f260c379cf0007b31bed'),
        'attachments': [{
            'files': [
                {'slug': '01', 'file': ObjectId('5679b25ec379cf25636688f6')},
                {'slug': '02b', 'file': ObjectId('5679b308c379cf25636688f7')},
                {'slug': '03', 'file': ObjectId('5679b33bc379cf25636688f8')},
            ],
            'field': 'properties.content'
        }],
    },
    '_updated': datetime.datetime(2016, 5, 2, 14, 19, 58, 0, tzinfo=tz_util.utc),
    'name': 'Image test',
    'project': EXAMPLE_PROJECT_OLD_ATTACHMENT_SCHEMA_ID,
    '_created': datetime.datetime(2016, 5, 2, 14, 19, 37, 0, tzinfo=tz_util.utc),
    '_etag': '6b8589b42c880e3626f43f3e82a5c5b946742687'
}

EXAMPLE_PAGE_NODE_OLD_ATTACHMENT_SCHEMA = {
    '_id': ObjectId('572761099837730efe8e120a'),
    'picture': ObjectId('5673f260c379cf0007b31bc4'),
    'description': '',
    'node_type': 'page',
    'user': ctd.EXAMPLE_PROJECT_OWNER_ID,
    'properties': {
        'status': 'published',
        'content': 'Überinteressant Verhaaltje™ voor het slapengaan.',
        'url': 'jemoeder',
        'attachments': [{
            'files': [
                {'slug': '03', 'file': ObjectId('5679b33bc379cf256366ddd8')},
                {'slug': '04', 'file': ObjectId('5679b35bc379cf256366ddd9')},
            ],
            'field': 'properties.content'
        }],
    },
    '_updated': datetime.datetime(2016, 5, 2, 14, 19, 58, 0, tzinfo=tz_util.utc),
    'name': 'Page test',
    'project': EXAMPLE_PROJECT_OLD_ATTACHMENT_SCHEMA_ID,
    '_created': datetime.datetime(2016, 5, 2, 14, 19, 37, 0, tzinfo=tz_util.utc),
    '_etag': '6b8589b42c880e3626f43f3e82a5c5b946742687'
}


class AbstractNodeReplacementTest(AbstractPillarTest):
    project_overrides = None

    def setUp(self, **kwargs):
        AbstractPillarTest.setUp(self, **kwargs)

        self.project_id, self.proj = self.ensure_project_exists(
            project_overrides=self.project_overrides)

        self.ensure_file_exists({
            '_id': EXAMPLE_PROJECT_OLD_ATTACHMENT_SCHEMA['picture_header'],
            'project': EXAMPLE_PROJECT_OLD_ATTACHMENT_SCHEMA_ID,
        })
        self.ensure_file_exists({
            '_id': EXAMPLE_PROJECT_OLD_ATTACHMENT_SCHEMA['picture_square'],
            'project': EXAMPLE_PROJECT_OLD_ATTACHMENT_SCHEMA_ID,
        })

    def fetch_project_from_db(self):
        return super(AbstractNodeReplacementTest, self).fetch_project_from_db(self.project_id)

    def add_group_permission_to_asset_node_type(self):
        group_perms = {'group': ctd.EXAMPLE_PROJECT_READONLY_GROUP_ID,
                       'methods': ['POST', 'PUT']}
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
        from pillar.cli.maintenance import replace_pillar_node_type_schemas

        group_perms = self.add_group_permission_to_asset_node_type()

        # Run the CLI command
        with self.app.test_request_context():
            replace_pillar_node_type_schemas(project_url=self.proj['url'])

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
            {'_id': EXAMPLE_ASSET_NODE_OLD_ATTACHMENT_SCHEMA['properties']['file']})

        for node in (EXAMPLE_ASSET_NODE_OLD_ATTACHMENT_SCHEMA,
                     EXAMPLE_PAGE_NODE_OLD_ATTACHMENT_SCHEMA):
            for att in node['properties']['attachments']:
                for filedict in att['files']:
                    self.ensure_file_exists({'_id': filedict['file']})

    def test_schema_upgrade(self):
        from pillar.cli.maintenance import upgrade_attachment_schema
        from pillar.api.node_types.asset import node_type_asset

        group_perms = self.add_group_permission_to_asset_node_type()

        with self.app.test_request_context():
            upgrade_attachment_schema(self.proj['url'], go=True)

        dbproj = self.fetch_project_from_db()

        # Test that the schemas were upgraded to the current schema.
        nt_asset = get_node_type(dbproj, 'asset')
        self.assertEqual(node_type_asset['dyn_schema']['attachments'],
                         nt_asset['dyn_schema']['attachments'])
        self.assertNotIn('attachments', nt_asset['form_schema'])

        # Test that the permissions set previously are still there.
        self.assertEqual([group_perms], nt_asset['permissions']['groups'])


class CreateBlogTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        AbstractPillarTest.setUp(self, **kwargs)

        self.project_id, self.proj = self.ensure_project_exists()
        self.ensure_file_exists({'_id': self.proj['picture_header']})
        self.ensure_file_exists({'_id': self.proj['picture_square']})

    def test_create_blog(self):
        """Very simple test to check the create_blog CLI command."""

        from pillar.cli.setup import create_blog

        with self.app.test_request_context():
            create_blog(self.proj['url'])

        dbproj = self.fetch_project_from_db()
        nt_blog = get_node_type(dbproj, 'blog')
        self.assertIsNotNone(nt_blog)

        # I trust that the blog node has been created too.
