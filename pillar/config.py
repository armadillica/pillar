from collections import defaultdict
import datetime
import os.path
from os import getenv

import requests.certs

# Certificate file for communication with other systems.
TLS_CERT_FILE = requests.certs.where()
print('Loading TLS certificates from %s' % TLS_CERT_FILE)

import requests.certs

RFC1123_DATE_FORMAT = '%a, %d %b %Y %H:%M:%S GMT'
PILLAR_SERVER_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCHEME = 'https'
PREFERRED_URL_SCHEME = SCHEME

# Be sure to set this in your config_local:
# SERVER_NAME = 'pillar.local:5000'
# PILLAR_SERVER_ENDPOINT = f'{SCHEME}://{SERVER_NAME}/api/'

STORAGE_DIR = getenv('PILLAR_STORAGE_DIR', '/data/storage/pillar')
PORT = 5000
HOST = '0.0.0.0'
DEBUG = False

# Flask and CSRF secret key; generate local one with:
# python3 -c 'import secrets; print(secrets.token_urlsafe(128))'
SECRET_KEY = ''

# Authentication token hashing key. If empty falls back to UTF8-encoded SECRET_KEY with a warning.
# Not used to hash new tokens, but it is used to check pre-existing hashed tokens.
AUTH_TOKEN_HMAC_KEY = b''

# Authentication settings
BLENDER_ID_ENDPOINT = 'http://id.local:8000/'

CDN_USE_URL_SIGNING = True
CDN_SERVICE_DOMAIN_PROTOCOL = 'https'
CDN_SERVICE_DOMAIN = '-CONFIG-THIS-'
CDN_CONTENT_SUBFOLDER = ''
CDN_URL_SIGNING_KEY = '-SECRET-'

CDN_STORAGE_USER = '-SECRET'
CDN_STORAGE_ADDRESS = 'push-11.cdnsun.com'
CDN_SYNC_LOGS = '/data/storage/logs'
CDN_RSA_KEY = '/data/config/cdnsun_id_rsa'
CDN_KNOWN_HOSTS = '/data/config/known_hosts'

UPLOADS_LOCAL_STORAGE_THUMBNAILS = {
    's': {'size': (90, 90), 'crop': True},
    'b': {'size': (160, 160), 'crop': True},
    't': {'size': (160, 160), 'crop': False},
    'm': {'size': (320, 320), 'crop': False},
    'l': {'size': (1024, 1024), 'crop': False},
    'h': {'size': (2048, 2048), 'crop': False}
}

BIN_FFPROBE = '/usr/bin/ffprobe'
BIN_FFMPEG = '/usr/bin/ffmpeg'
BIN_SSH = '/usr/bin/ssh'
BIN_RSYNC = '/usr/bin/rsync'

GCLOUD_APP_CREDENTIALS = 'google_app.json'
GCLOUD_PROJECT = '-SECRET-'
# Used for cross-verification on various Google sites (eg. YouTube)
GOOGLE_SITE_VERIFICATION = ''

ADMIN_USER_GROUP = '5596e975ea893b269af85c0e'
SUBSCRIBER_USER_GROUP = '5596e975ea893b269af85c0f'

SENTRY_CONFIG = {
    'dsn': '-set-in-config-local-',
    # 'release': raven.fetch_git_sha(os.path.dirname(__file__)),
}
# See https://docs.sentry.io/clients/python/integrations/flask/#settings
SENTRY_USER_ATTRS = ['username', 'full_name', 'email', 'objectid']

ALGOLIA_USER = '-SECRET-'
ALGOLIA_API_KEY = '-SECRET-'
ALGOLIA_INDEX_USERS = 'dev_Users'
ALGOLIA_INDEX_NODES = 'dev_Nodes'

SEARCH_BACKENDS = ('elastic', )

ELASTIC_INDICES = {
    'NODE': 'nodes',
    'USER': 'users',
}

ELASTIC_SEARCH_HOSTS = ['elastic:9200']


ZENCODER_API_KEY = '-SECRET-'
ZENCODER_NOTIFICATIONS_SECRET = '-SECRET-'
ZENCODER_NOTIFICATIONS_URL = 'http://zencoderfetcher/'

ENCODING_BACKEND = 'zencoder'  # local, flamenco

# Storage solution for uploaded files. If 'local' is selected, make sure you specify the SERVER_NAME
# config value as well, since it will help building correct URLs when indexing.
STORAGE_BACKEND = 'local'  # gcs

# Validity period of links, per file storage backend. Expressed in seconds.
# Shouldn't be more than a year, as this isn't supported by HTTP/1.1.
FILE_LINK_VALIDITY = defaultdict(
    lambda: 3600 * 24 * 30,  # default of 1 month.
    gcs=3600 * 23,  # 23 hours for Google Cloud Storage.
)

# Capability with GET-access to all variations of files.
FULL_FILE_ACCESS_CAP = 'subscriber'

# Client and Subclient IDs for Blender ID
BLENDER_ID_CLIENT_ID = 'SPECIAL-SNOWFLAKE-57'
BLENDER_ID_SUBCLIENT_ID = 'PILLAR'

# Blender ID user info API endpoint URL and auth token, used for
# reconciling subscribers and updating their info from /u/.
# The token requires the 'userinfo' scope.
BLENDER_ID_USER_INFO_API = 'http://blender-id:8000/api/user/'
BLENDER_ID_USER_INFO_TOKEN = '-set-in-config-local-'

# Collection of supported OAuth providers (Blender ID, Facebook and Google).
# Example entry:
# OAUTH_CREDENTIALS = {
#    'blender-id': {
#        'id': 'CLOUD-OF-SNOWFLAKES-42',
#        'secret': 'thesecret',
#     }
# }
# OAuth providers are defined in pillar.auth.oauth
OAUTH_CREDENTIALS = {
    'blender-id': {},
    'facebook': {},
    'google': {},
}

# See https://docs.python.org/2/library/logging.config.html#configuration-dictionary-schema
LOGGING = {
    'version': 1,
    'formatters': {
        'default': {'format': '%(asctime)-15s %(levelname)8s %(name)s %(message)s'}
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
            'stream': 'ext://sys.stderr',
        }
    },
    'loggers': {
        'pillar': {'level': 'INFO'},
        'werkzeug': {'level': 'INFO'},
    },
    'root': {
        'level': 'WARNING',
        'handlers': [
            'console',
        ],
    }
}

SHORT_LINK_BASE_URL = 'https://blender.cloud/r/'
SHORT_CODE_LENGTH = 6  # characters

# People are allowed this many bytes per uploaded file.
FILESIZE_LIMIT_BYTES_NONSUBS = 32 * 2 ** 20
# Unless they have one of those roles.
ROLES_FOR_UNLIMITED_UPLOADS = {'subscriber', 'demo', 'admin'}

ROLES_FOR_COMMENT_VOTING = {'subscriber', 'demo'}

#############################################
# Old pillar-web config:

# Mapping from /{path} to URL to redirect to.
REDIRECTS = {}

GIT = 'git'

# Setting this to True can be useful for development.
# Note that it doesn't add the /p/home/{node-id} endpoint, so you will have to
# change the URL of the home project if you want to have direct access to nodes.
RENDER_HOME_AS_REGULAR_PROJECT = False


# Blender Cloud add-on version. This updates the value in all places in the
# front-end.
BLENDER_CLOUD_ADDON_VERSION = '1.4'

# Certificate file for communication with other systems.
TLS_CERT_FILE = requests.certs.where()

CELERY_BACKEND = 'redis://redis/1'
CELERY_BROKER = 'redis://redis/2'

# This configures the Celery task scheduler in such a way that we don't
# have to import the pillar.celery.XXX modules. Remember to run
# 'manage.py celery beat' too, otherwise those will never run.
CELERY_BEAT_SCHEDULE = {
    'regenerate-expired-links': {
        'task': 'pillar.celery.file_link_tasks.regenerate_all_expired_links',
        'schedule': 600,  # every N seconds
        'args': ('gcs', 100)
    },
    'refresh-blenderid-badges': {
        'task': 'pillar.celery.badges.sync_badges_for_users',
        'schedule': 10 * 60,  # every N seconds
        'args': (9 * 60, ),  # time limit in seconds, keep shorter than 'schedule'
    }
}

# Badges will be re-fetched every timedelta.
# TODO(Sybren): A proper value should be determined after we actually have users with badges.
BLENDER_ID_BADGE_EXPIRY = datetime.timedelta(hours=4)

# How many times the Celery task for downloading an avatar is retried.
AVATAR_DOWNLOAD_CELERY_RETRY = 3

# Mapping from user role to capabilities obtained by users with that role.
USER_CAPABILITIES = defaultdict(**{
    'subscriber': {'subscriber', 'home-project'},
    'demo': {'subscriber', 'home-project'},
    'admin': {'encode-video', 'admin',
              'view-pending-nodes', 'edit-project-node-types', 'create-organization'},
    'video-encoder': {'encode-video'},
    'org-subscriber': {'subscriber', 'home-project'},
}, default_factory=frozenset)


# Internationalization and localization

# The default locale is US English.
# A locale can include a territory, a codeset and a modifier.
# We only support locale strings with or without territories though.
# For example, nl_NL and pt_BR are not the same language as nl_BE, and pt_PT.
# However we can have a nl, or a pt translation, to be used as a common
# translation when no territorial specific locale is available.
# All translations should be in UTF-8.
# This setting is used as a fallback when there is no good match between the
# browser language and the available translations.
DEFAULT_LOCALE = 'en_US'
# All the available languages will be determined based on available translations
# in the //translations/ folder. The exception is English, since all the text is
# originally in English already. That said, if rare occasions we may want to
# never show the site in English.
SUPPORT_ENGLISH = True


# Mail options, see pillar.celery.email_tasks.
SMTP_HOST = 'localhost'
SMTP_PORT = 2525
SMTP_USERNAME = ''
SMTP_PASSWORD = ''
SMTP_TIMEOUT = 30  # timeout in seconds, https://docs.python.org/3/library/smtplib.html#smtplib.SMTP
MAIL_RETRY = 180  # in seconds, delay until trying to send an email again.
MAIL_DEFAULT_FROM_NAME = 'Blender Cloud'
MAIL_DEFAULT_FROM_ADDR = 'cloudsupport@localhost'

SEND_FILE_MAX_AGE_DEFAULT = 3600 * 24 * 365  # seconds

# MUST be 8 characters long, see pillar.flask_extra.HashedPathConverter
# Intended to be changed for every deploy. If it is empty, a random hash will
# be used. Note that this causes extra traffic, since every time the process
# restarts the URLs will be different.
STATIC_FILE_HASH = ''

# Disable default CSRF protection for all views, since most web endpoints and
# all API endpoints do not need it. On the views that require it, we use the
# current_app.csrf.protect() method.
WTF_CSRF_CHECK_DEFAULT = False

# Flask Debug Toolbar. Enable it by overriding DEBUG_TB_ENABLED in config_local.py.
DEBUG_TB_ENABLED = False
DEBUG_TB_PANELS = [
    'flask_debugtoolbar.panels.versions.VersionDebugPanel',
    'flask_debugtoolbar.panels.headers.HeaderDebugPanel',
    'flask_debugtoolbar.panels.request_vars.RequestVarsDebugPanel',
    'flask_debugtoolbar.panels.config_vars.ConfigVarsDebugPanel',
    'flask_debugtoolbar.panels.template.TemplateDebugPanel',
    'flask_debugtoolbar.panels.logger.LoggingPanel',
    'flask_debugtoolbar.panels.route_list.RouteListDebugPanel']
