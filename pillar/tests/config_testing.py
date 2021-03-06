"""Flask configuration file for unit testing."""

BLENDER_ID_ENDPOINT = 'http://id.local:8001/'  # Non existant server

SERVER_NAME = 'localhost.local'
PILLAR_SERVER_ENDPOINT = 'http://localhost.local/api/'

MAIN_PROJECT_ID = '5672beecc0261b2005ed1a33'

DEBUG = False
TESTING = True

CDN_STORAGE_USER = 'u41508580125621'

FILESIZE_LIMIT_BYTES_NONSUBS = 20 * 2 ** 10
ROLES_FOR_UNLIMITED_UPLOADS = {'subscriber', 'demo', 'admin'}

GCLOUD_APP_CREDENTIALS = 'invalid-file-because-gcloud-storage-should-be-mocked-in-tests'
STORAGE_BACKEND = 'local'

EXTERNAL_SUBSCRIPTIONS_MANAGEMENT_SERVER = "http://store.localhost/api"

SECRET_KEY = '12345'

OAUTH_CREDENTIALS = {
    'blender-id': {
        'id': 'blender-id-app-id',
        'secret': 'blender-id–secret',
    },
    'facebook': {
        'id': 'fb-app-id',
        'secret': 'facebook-secret'
    },
    'google': {
        'id': 'google-app-id',
        'secret': 'google-secret'
    }
}

ELASTIC_INDICES = {
    'NODE': 'test_nodes',
    'USER': 'test_users',
}

# MUST be 8 characters long, see pillar.flask_extra.HashedPathConverter
STATIC_FILE_HASH = 'abcd1234'

CACHE_NO_NULL_WARNING = True
