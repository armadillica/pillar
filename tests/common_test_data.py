import datetime

from bson import tz_util, ObjectId

EXAMPLE_PROJECT_ID = ObjectId('5672beecc0261b2005ed1a33')

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
                     u'size': 'h'}, ],
                u'filename': 'brick_dutch_soft_bump.png',
                u'project': EXAMPLE_PROJECT_ID,
                u'width': 2048, u'length': 6227670, u'user': ObjectId('56264fc4fa3a250344bd10c5'),
                u'content_type': 'image/png', u'_etag': '044ce3aede2e123e261c0d8bd77212f264d4f7b0',
                u'_created': datetime.datetime(2015, 12, 17, 16, 28, 49, tzinfo=tz_util.utc),
                u'md5': '',
                u'file_path': 'c2a5c897769ce1ef0eb10f8fa1c472bcb8e2d5a4.png', u'backend': 'gcs',
                u'link': 'http://localhost:8002/file',
                u'link_expires': datetime.datetime(2016, 3, 22, 9, 28, 22, tzinfo=tz_util.utc)}


EXAMPLE_PROJECT = {
    u'_created': datetime.datetime(2015, 12, 17, 13, 22, 56, tzinfo=tz_util.utc),
    u'_etag': u'cc4643e98d3606f87bbfaaa200bfbae941b642f3',
    u'_id': EXAMPLE_PROJECT_ID,
    u'_updated': datetime.datetime(2016, 1, 7, 18, 59, 4, tzinfo=tz_util.utc),
    u'category': u'assets',
    u'description': u'Welcome to this curated collection of Blender Institute textures and image resources. This collection is an on-going project, as with each project we create a number of textures based on our own resources (photographs, scans, etc.) or made completely from scratch. At the moment you can find all the textures from the past Open Projects that were deemed re-usable. \r\n\r\nPeople who have contributed to these textures:\r\n\r\nAndrea Weikert, Andy Goralczyk, Basse Salmela, Ben Dansie, Campbell Barton, Enrico Valenza, Ian Hubert, Kjartan Tysdal, Manu J\xe4rvinen, Massimiliana Pulieso, Matt Ebb, Pablo Vazquez, Rob Tuytel, Roland Hess, Sarah Feldlaufer, S\xf6nke M\xe4ter',
    u'is_private': False,
    u'name': u'Textures',
    u'node_types': [{u'description': u'Group for texture node type',
                     u'dyn_schema': {u'order': {u'type': u'integer'},
                                     u'status': {u'allowed': [u'published', u'pending', u'deleted'],
                                                 u'type': u'string'},
                                     u'url': {u'type': u'string'}},
                     u'form_schema': {u'order': {}, u'status': {}, u'url': {}},
                     u'name': u'group_texture',
                     u'parent': [u'group_texture', u'project'],
                     u'permissions': {u'groups': [{u'group': ObjectId('5596e975ea893b269af85c0e'),
                                                   u'methods': [u'GET', u'PUT', u'POST']},
                                                  {u'group': ObjectId('5596e975ea893b269af85c0f'),
                                                   u'methods': [u'GET']},
                                                  {u'group': ObjectId('564733b56dcaf85da2faee8a'),
                                                   u'methods': [u'GET']},
                                                  {u'group': ObjectId('564c52b96dcaf85da2faef00'),
                                                   u'methods': [u'GET', u'POST']}],
                                      u'users': [],
                                      u'world': [u'GET']}},
                    {u'description': u'Generic group node type edited',
                     u'dyn_schema': {u'notes': {u'maxlength': 256, u'type': u'string'},
                                     u'order': {u'type': u'integer'},
                                     u'status': {u'allowed': [u'published', u'pending', u'deleted'],
                                                 u'type': u'string'},
                                     u'url': {u'type': u'string'}},
                     u'form_schema': {u'notes': {}, u'order': {}, u'status': {}, u'url': {}},
                     u'name': u'group',
                     u'parent': [u'group', u'project'],
                     u'permissions': {u'groups': [{u'group': ObjectId('5596e975ea893b269af85c0e'),
                                                   u'methods': [u'GET', u'PUT', u'POST']},
                                                  {u'group': ObjectId('5596e975ea893b269af85c0f'),
                                                   u'methods': [u'GET']},
                                                  {u'group': ObjectId('564733b56dcaf85da2faee8a'),
                                                   u'methods': [u'GET']}],
                                      u'users': [],
                                      u'world': [u'GET']}},
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
                                                  u'processing',
                                                  u'deleted'],
                                     u'type': u'string'},
                         u'tags': {u'schema': {u'type': u'string'}, u'type': u'list'}},
                     u'form_schema': {u'attachments': {u'visible': False},
                                      u'categories': {},
                                      u'content_type': {u'visible': False},
                                      u'file': {u'visible': False},
                                      u'order': {},
                                      u'status': {},
                                      u'tags': {}},
                     u'name': u'asset',
                     u'parent': [u'group'],
                     u'permissions': {u'groups': [{u'group': ObjectId('5596e975ea893b269af85c0e'),
                                                   u'methods': [u'GET', u'PUT', u'POST']},
                                                  {u'group': ObjectId('5596e975ea893b269af85c0f'),
                                                   u'methods': [u'GET']},
                                                  {u'group': ObjectId('564733b56dcaf85da2faee8a'),
                                                   u'methods': [u'GET']}],
                                      u'users': [],
                                      u'world': [u'GET']}},
                    {u'description': u'Entrypoint to a remote or local storage solution',
                     u'dyn_schema': {u'backend': {u'type': u'string'},
                                     u'subdir': {u'type': u'string'}},
                     u'form_schema': {u'backend': {}, u'subdir': {}},
                     u'name': u'storage',
                     u'parent': [u'group', u'project'],
                     u'permissions': {u'groups': [{u'group': ObjectId('5596e975ea893b269af85c0e'),
                                                   u'methods': [u'GET', u'PUT', u'POST']},
                                                  {u'group': ObjectId('5596e975ea893b269af85c0f'),
                                                   u'methods': [u'GET']},
                                                  {u'group': ObjectId('564733b56dcaf85da2faee8a'),
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
                                     u'status': {u'allowed': [u'published', u'deleted', u'flagged',
                                                              u'edited'],
                                                 u'type': u'string'}},
                     u'form_schema': {u'confidence': {},
                                      u'content': {},
                                      u'is_reply': {},
                                      u'rating_negative': {},
                                      u'rating_positive': {},
                                      u'ratings': {},
                                      u'status': {}},
                     u'name': u'comment',
                     u'parent': [u'asset', u'comment'],
                     u'permissions': {u'groups': [{u'group': ObjectId('5596e975ea893b269af85c0e'),
                                                   u'methods': [u'GET', u'PUT', u'POST']},
                                                  {u'group': ObjectId('5596e975ea893b269af85c0f'),
                                                   u'methods': [u'GET', u'POST']},
                                                  {u'group': ObjectId('564733b56dcaf85da2faee8a'),
                                                   u'methods': [u'GET', u'POST']}],
                                      u'users': [],
                                      u'world': [u'GET']}},
                    {u'description': u'Container for node_type post.',
                     u'dyn_schema': {u'categories': {u'schema': {u'type': u'string'},
                                                     u'type': u'list'},
                                     u'template': {u'type': u'string'}},
                     u'form_schema': {u'categories': {}, u'template': {}},
                     u'name': u'blog',
                     u'parent': [u'project'],
                     u'permissions': {u'groups': [{u'group': ObjectId('5596e975ea893b269af85c0e'),
                                                   u'methods': [u'GET', u'PUT', u'POST']}],
                                      u'users': [],
                                      u'world': [u'GET']}},
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
                         u'status': {u'allowed': [u'published', u'deleted', u'pending'],
                                     u'default': u'pending',
                                     u'type': u'string'},
                         u'url': {u'type': u'string'}},
                     u'form_schema': {u'attachments': {u'visible': False},
                                      u'category': {},
                                      u'content': {},
                                      u'status': {},
                                      u'url': {}},
                     u'name': u'post',
                     u'parent': [u'blog'],
                     u'permissions': {u'groups': [{u'group': ObjectId('5596e975ea893b269af85c0e'),
                                                   u'methods': [u'GET', u'PUT', u'POST']}],
                                      u'users': [],
                                      u'world': [u'GET']}},
                    {u'description': u'Image Texture',
                     u'dyn_schema': {u'aspect_ratio': {u'type': u'float'},
                                     u'categories': {u'type': u'string'},
                                     u'files': {u'schema': {u'schema': {
                                         u'file': {u'data_relation': {u'embeddable': True,
                                                                      u'field': u'_id',
                                                                      u'resource': u'files'},
                                                   u'type': u'objectid'},
                                         u'is_tileable': {u'type': u'boolean'},
                                         u'map_type': {u'allowed': [u'spec',
                                                                    u'bump',
                                                                    u'nor',
                                                                    u'col',
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
                                     u'stat_ensure_file_existsus': {u'allowed': [u'published',
                                                              u'pending',
                                                              u'processing',
                                                              u'deleted'],
                                                 u'type': u'string'},
                                     u'tags': {u'schema': {u'type': u'string'}, u'type': u'list'}},
                     u'form_schema': {u'aspect_ratio': {},
                                      u'categories': {},
                                      u'content_type': {u'visible': False},
                                      u'files': {u'visible': False},
                                      u'is_landscape': {},
                                      u'is_tileable': {},
                                      u'order': {},
                                      u'resolution': {},
                                      u'status': {},
                                      u'tags': {}},
                     u'name': u'texture',
                     u'parent': [u'group'],
                     u'permissions': {u'groups': [{u'group': ObjectId('5596e975ea893b269af85c0e'),
                                                   u'methods': [u'GET', u'PUT', u'POST']},
                                                  {u'group': ObjectId('5596e975ea893b269af85c0f'),
                                                   u'methods': [u'GET']},
                                                  {u'group': ObjectId('564733b56dcaf85da2faee8a'),
                                                   u'methods': [u'GET']}],
                                      u'users': [],
                                      u'world': [u'GET']}}],
    u'nodes_blog': [],
    u'nodes_featured': [],
    u'nodes_latest': [],
    u'organization': ObjectId('55a99fb43004867fb9934f01'),
    u'owners': {u'groups': [], u'users': []},
    u'permissions': {u'groups': [{u'group': ObjectId('5596e975ea893b269af85c0e'),
                                  u'methods': [u'GET', u'PUT', u'POST']}],
                     u'users': [],
                     u'world': [u'GET']},
    u'picture_header': ObjectId('5673f260c379cf0007b31bc4'),
    u'picture_square': ObjectId('5673f256c379cf0007b31bc3'),
    u'status': u'published',
    u'summary': u'Texture collection from all Blender Institute open projects.',
    u'url': u'textures',
    u'user': ObjectId('552b066b41acdf5dec4436f2')}