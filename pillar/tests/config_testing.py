"""Flask configuration file for unit testing."""

BLENDER_ID_ENDPOINT = 'http://127.0.0.1:8001'  # nonexistant server, no trailing slash!

DEBUG = False
TESTING = True

CDN_STORAGE_USER = 'u41508580125621'

FILESIZE_LIMIT_BYTES_NONSUBS = 20 * 2 ** 10
ROLES_FOR_UNLIMITED_UPLOADS = {'subscriber', 'demo', 'admin'}

GCLOUD_APP_CREDENTIALS = 'invalid-file-because-gcloud-storage-should-be-mocked-in-tests'
STORAGE_BACKEND = 'local'

EXTERNAL_SUBSCRIPTIONS_MANAGEMENT_SERVER = "http://store.localhost/api"
