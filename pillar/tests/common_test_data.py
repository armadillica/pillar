import datetime

from bson import tz_util, ObjectId

from pillar.api.node_types import PILLAR_NAMED_NODE_TYPES

EXAMPLE_ADMIN_GROUP_ID = ObjectId('5596e975ea893b269af85c0e')
EXAMPLE_PROJECT_READONLY_GROUP_ID = ObjectId('5596e975ea893b269af85c0f')
EXAMPLE_PROJECT_READONLY_GROUP2_ID = ObjectId('564733b56dcaf85da2faee8a')

EXAMPLE_PROJECT_ID = ObjectId('5672beecc0261b2005ed1a33')
EXAMPLE_PROJECT_OWNER_ID = ObjectId('552b066b41acdf5dec4436f2')

EXAMPLE_FILE = {u'_id': ObjectId('5672e2c1c379cf0007b31995'),
                u'_updated': datetime.datetime(2016, 3, 25, 10, 28, 24, tzinfo=tz_util.utc),
                u'height': 2048,
                u'name': 'c2a5c897769ce1ef0eb10f8fa1c472bcb8e2d5a4.png', u'format': 'png',
                u'variations': [
                    {u'format': 'jpg', u'height': 160, u'width': 160, u'length': 8558,
                     u'link': 'http://localhost:8002/file-variant-h', u'content_type': 'image/jpeg',
                     u'md5': '--', u'file_path': 'c2a5c897769ce1ef0eb10f8fa1c472bcb8e2d5a4-b.jpg',
                     u'size': 'b'},
                    {u'format': 'jpg', u'height': 2048, u'width': 2048, u'length': 819569,
                     u'link': 'http://localhost:8002/file-variant-h', u'content_type': 'image/jpeg',
                     u'md5': '--', u'file_path': 'c2a5c897769ce1ef0eb10f8fa1c472bcb8e2d5a4-h.jpg',
                     u'size': 'h'},
                    {u'format': 'jpg', u'height': 64, u'width': 64, u'length': 8195,
                     u'link': 'http://localhost:8002/file-variant-t', u'content_type': 'image/jpeg',
                     u'md5': '--', u'file_path': 'c2a5c897769ce1ef0eb10f8fa1c472bcb8e2d5a4-t.jpg',
                     u'size': 't'},
                ],
                u'filename': 'brick_dutch_soft_bump.png',
                u'project': EXAMPLE_PROJECT_ID,
                u'width': 2048, u'length': 6227670,
                u'user': ObjectId('56264fc4fa3a250344bd10c5'),
                u'content_type': 'image/png',
                u'_etag': '044ce3aede2e123e261c0d8bd77212f264d4f7b0',
                u'_created': datetime.datetime(2015, 12, 17, 16, 28, 49, tzinfo=tz_util.utc),
                u'md5': '',
                u'file_path': 'c2a5c897769ce1ef0eb10f8fa1c472bcb8e2d5a4.png',
                u'backend': 'pillar',
                u'link': 'http://localhost:8002/file',
                u'link_expires': datetime.datetime(2016, 3, 22, 9, 28, 22, tzinfo=tz_util.utc)}

EXAMPLE_PROJECT = {
    u'_created': datetime.datetime(2015, 12, 17, 13, 22, 56, tzinfo=tz_util.utc),
    u'_etag': u'cc4643e98d3606f87bbfaaa200bfbae941b642f3',
    u'_id': EXAMPLE_PROJECT_ID,
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
        PILLAR_NAMED_NODE_TYPES['group_texture'],
        PILLAR_NAMED_NODE_TYPES['group'],
        PILLAR_NAMED_NODE_TYPES['asset'],
        PILLAR_NAMED_NODE_TYPES['storage'],
        PILLAR_NAMED_NODE_TYPES['comment'],
        PILLAR_NAMED_NODE_TYPES['blog'],
        PILLAR_NAMED_NODE_TYPES['post'],
        PILLAR_NAMED_NODE_TYPES['texture'],
    ],
    u'nodes_blog': [],
    u'nodes_featured': [],
    u'nodes_latest': [],
    u'permissions': {u'groups': [{u'group': EXAMPLE_ADMIN_GROUP_ID,
                                  u'methods': [u'GET', u'POST', u'PUT', u'DELETE']}],
                     u'users': [],
                     u'world': [u'GET']},
    u'picture_header': ObjectId('5673f260c379cf0007b31bc4'),
    u'picture_square': ObjectId('5673f256c379cf0007b31bc3'),
    u'status': u'published',
    u'summary': u'Texture collection from all Blender Institute open projects.',
    u'url': u'textures',
    u'user': EXAMPLE_PROJECT_OWNER_ID}

EXAMPLE_NODE = {
    u'_id': ObjectId('572761099837730efe8e120d'),
    u'picture': ObjectId('572761f39837730efe8e1210'),
    u'description': u'',
    u'node_type': u'asset',
    u'user': ObjectId('57164ca1983773118cbaf779'),
    u'properties': {
        u'status': u'published',
        u'content_type': u'image',
        u'file': ObjectId('572761129837730efe8e120e')
    },
    u'_updated': datetime.datetime(2016, 5, 2, 14, 19, 58, 0, tzinfo=tz_util.utc),
    u'name': u'Image test',
    u'project': EXAMPLE_PROJECT_ID,
    u'_created': datetime.datetime(2016, 5, 2, 14, 19, 37, 0, tzinfo=tz_util.utc),
    u'_etag': u'6b8589b42c880e3626f43f3e82a5c5b946742687'
}

BLENDER_ID_TEST_USERID = 1533
EXAMPLE_USER = {'_id': EXAMPLE_PROJECT_OWNER_ID,
                'username': 'sybren+unittests@blender.studio',
                'groups': [],
                'auth': [{
                    'provider': 'blender-id',
                    'token': '',
                    'user_id': str(BLENDER_ID_TEST_USERID),
                }],
                'full_name': 'sybren+unittest@blender.studio',
                'settings': {'email_communications': 1},
                '_updated': datetime.datetime(2016, 8, 5, 18, 19, 29),
                '_etag': '25a6a90781bf27333218fbbf33b3e8d53e37b1cb',
                '_created': datetime.datetime(2016, 8, 5, 18, 19, 29),
                'email': 'sybren+unittests@blender.studio'}
