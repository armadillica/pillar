import datetime

from bson import tz_util, ObjectId

from pillar.api.node_types import PILLAR_NAMED_NODE_TYPES

EXAMPLE_ADMIN_GROUP_ID = ObjectId('5596e975ea893b269af85c0e')
EXAMPLE_PROJECT_READONLY_GROUP_ID = ObjectId('5596e975ea893b269af85c0f')
EXAMPLE_PROJECT_READONLY_GROUP2_ID = ObjectId('564733b56dcaf85da2faee8a')

EXAMPLE_PROJECT_ID = ObjectId('5672beecc0261b2005ed1a33')
EXAMPLE_PROJECT_OWNER_ID = ObjectId('552b066b41acdf5dec4436f2')

EXAMPLE_FILE = {'_id': ObjectId('5672e2c1c379cf0007b31995'),
                '_updated': datetime.datetime(2016, 3, 25, 10, 28, 24, tzinfo=tz_util.utc),
                'height': 2048,
                'name': 'c2a5c897769ce1ef0eb10f8fa1c472bcb8e2d5a4.png', 'format': 'png',
                'variations': [
                    {'format': 'jpg', 'height': 160, 'width': 160, 'length': 8558,
                     'link': 'http://localhost:8002/file-variant-h', 'content_type': 'image/jpeg',
                     'md5': '--', 'file_path': 'c2a5c897769ce1ef0eb10f8fa1c472bcb8e2d5a4-b.jpg',
                     'size': 'b'},
                    {'format': 'jpg', 'height': 2048, 'width': 2048, 'length': 819569,
                     'link': 'http://localhost:8002/file-variant-h', 'content_type': 'image/jpeg',
                     'md5': '--', 'file_path': 'c2a5c897769ce1ef0eb10f8fa1c472bcb8e2d5a4-h.jpg',
                     'size': 'h'},
                    {'format': 'jpg', 'height': 64, 'width': 64, 'length': 8195,
                     'link': 'http://localhost:8002/file-variant-t', 'content_type': 'image/jpeg',
                     'md5': '--', 'file_path': 'c2a5c897769ce1ef0eb10f8fa1c472bcb8e2d5a4-t.jpg',
                     'size': 't'},
                ],
                'filename': 'brick_dutch_soft_bump.png',
                'project': EXAMPLE_PROJECT_ID,
                'width': 2048, 'length': 6227670,
                'user': ObjectId('56264fc4fa3a250344bd10c5'),
                'content_type': 'image/png',
                '_etag': '044ce3aede2e123e261c0d8bd77212f264d4f7b0',
                '_created': datetime.datetime(2015, 12, 17, 16, 28, 49, tzinfo=tz_util.utc),
                'md5': '',
                'file_path': 'c2a5c897769ce1ef0eb10f8fa1c472bcb8e2d5a4.png',
                'backend': 'pillar',
                'link': 'http://localhost:8002/file',
                'link_expires': datetime.datetime(2016, 3, 22, 9, 28, 22, tzinfo=tz_util.utc)}

EXAMPLE_PROJECT = {
    '_created': datetime.datetime(2015, 12, 17, 13, 22, 56, tzinfo=tz_util.utc),
    '_etag': 'cc4643e98d3606f87bbfaaa200bfbae941b642f3',
    '_id': EXAMPLE_PROJECT_ID,
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
        PILLAR_NAMED_NODE_TYPES['group_texture'],
        PILLAR_NAMED_NODE_TYPES['group'],
        PILLAR_NAMED_NODE_TYPES['asset'],
        PILLAR_NAMED_NODE_TYPES['storage'],
        PILLAR_NAMED_NODE_TYPES['comment'],
        PILLAR_NAMED_NODE_TYPES['blog'],
        PILLAR_NAMED_NODE_TYPES['post'],
        PILLAR_NAMED_NODE_TYPES['texture'],
    ],
    'nodes_blog': [],
    'nodes_featured': [],
    'nodes_latest': [],
    'permissions': {'groups': [{'group': EXAMPLE_ADMIN_GROUP_ID,
                                  'methods': ['GET', 'POST', 'PUT', 'DELETE']}],
                     'users': [],
                     'world': ['GET']},
    'picture_header': ObjectId('5673f260c379cf0007b31bc4'),
    'picture_square': ObjectId('5673f256c379cf0007b31bc3'),
    'status': 'published',
    'summary': 'Texture collection from all Blender Institute open projects.',
    'url': 'default-project',
    'user': EXAMPLE_PROJECT_OWNER_ID}

EXAMPLE_NODE = {
    '_id': ObjectId('572761099837730efe8e120d'),
    'picture': ObjectId('572761f39837730efe8e1210'),
    'description': '',
    'node_type': 'asset',
    'user': ObjectId('57164ca1983773118cbaf779'),
    'properties': {
        'status': 'published',
        'content_type': 'image',
        'file': ObjectId('572761129837730efe8e120e')
    },
    '_updated': datetime.datetime(2016, 5, 2, 14, 19, 58, 0, tzinfo=tz_util.utc),
    'name': 'Image test',
    'project': EXAMPLE_PROJECT_ID,
    '_created': datetime.datetime(2016, 5, 2, 14, 19, 37, 0, tzinfo=tz_util.utc),
    '_etag': '6b8589b42c880e3626f43f3e82a5c5b946742687'
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
