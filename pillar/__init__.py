"""Pillar server."""

import collections
import copy
import json
import logging
import logging.config
import subprocess
import tempfile
import typing
import os
import os.path

import jinja2
from eve import Eve
import flask
from flask import render_template, request
from flask.templating import TemplateNotFound
import pymongo.collection
import pymongo.database

from pillar.api import custom_field_validation
from pillar.api.utils import authentication
import pillar.web.jinja

from . import api
from . import web
from . import auth

empty_settings = {
    # Use a random URL prefix when booting Eve, to ensure that any
    # Flask route that's registered *before* we load our own config
    # won't interfere with Pillar itself.
    'URL_PREFIX': 'pieQui4vah9euwieFai6naivaV4thahchoochiiwazieBe5o',
    'DOMAIN': {},
}


class PillarServer(Eve):
    def __init__(self, app_root, **kwargs):
        kwargs.setdefault('validator', custom_field_validation.ValidateCustomFields)
        super(PillarServer, self).__init__(settings=empty_settings, **kwargs)

        # mapping from extension name to extension object.
        self.pillar_extensions = collections.OrderedDict()
        self.pillar_extensions_template_paths = []  # list of paths

        self.app_root = os.path.abspath(app_root)
        self._load_flask_config()
        self._config_logging()

        self.log = logging.getLogger('%s.%s' % (__name__, self.__class__.__name__))
        self.log.info('Creating new instance from %r', self.app_root)

        self._config_tempdirs()
        self._config_git()
        self._config_bugsnag()
        self._config_google_cloud_storage()

        self.algolia_index_users = None
        self.algolia_index_nodes = None
        self.algolia_client = None
        self._config_algolia()

        self.encoding_service_client = None
        self._config_encoding_backend()

        try:
            self.settings = os.environ['EVE_SETTINGS']
        except KeyError:
            self.settings = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         'api', 'eve_settings.py')
        # self.settings = self.config['EVE_SETTINGS_PATH']
        self.load_config()

        # Configure authentication
        self.login_manager = auth.config_login_manager(self)
        self.oauth_blender_id = auth.config_oauth_login(self)

        self._config_caching()

        self.before_first_request(self.setup_db_indices)

    def _load_flask_config(self):
        # Load configuration from different sources, to make it easy to override
        # settings with secrets, as well as for development & testing.
        self.config.from_pyfile(os.path.join(os.path.dirname(__file__), 'config.py'), silent=False)
        self.config.from_pyfile(os.path.join(self.app_root, 'config.py'), silent=True)
        self.config.from_pyfile(os.path.join(self.app_root, 'config_local.py'), silent=True)
        from_envvar = os.environ.get('PILLAR_CONFIG')
        if from_envvar:
            # Don't use from_envvar, as we want different behaviour. If the envvar
            # is not set, it's fine (i.e. silent=True), but if it is set and the
            # configfile doesn't exist, it should error out (i.e. silent=False).
            self.config.from_pyfile(from_envvar, silent=False)

    def _config_logging(self):
        # Configure logging
        logging.config.dictConfig(self.config['LOGGING'])
        log = logging.getLogger(__name__)
        if self.config['DEBUG']:
            log.info('Pillar starting, debug=%s', self.config['DEBUG'])

    def _config_tempdirs(self):
        storage_dir = self.config['STORAGE_DIR']
        if not os.path.exists(storage_dir):
            self.log.info('Creating storage directory %r', storage_dir)
            os.makedirs(storage_dir)

        # Set the TMP environment variable to manage where uploads are stored.
        # These are all used by tempfile.mkstemp(), but we don't knwow in whic
        # order. As such, we remove all used variables but the one we set.
        tempfile.tempdir = storage_dir
        os.environ['TMP'] = storage_dir
        os.environ.pop('TEMP', None)
        os.environ.pop('TMPDIR', None)

    def _config_git(self):
        # Get the Git hash
        try:
            git_cmd = ['git', '-C', self.app_root, 'describe', '--always']
            description = subprocess.check_output(git_cmd)
            self.config['GIT_REVISION'] = description.strip()
        except (subprocess.CalledProcessError, OSError) as ex:
            self.log.warning('Unable to run "git describe" to get git revision: %s', ex)
            self.config['GIT_REVISION'] = 'unknown'
        self.log.info('Git revision %r', self.config['GIT_REVISION'])

    def _config_bugsnag(self):
        # Configure Bugsnag
        if self.config.get('TESTING') or not self.config.get('BUGSNAG_API_KEY'):
            self.log.info('Bugsnag NOT configured.')
            return

        import bugsnag
        from bugsnag.flask import handle_exceptions
        from bugsnag.handlers import BugsnagHandler

        bugsnag.configure(
            api_key=self.config['BUGSNAG_API_KEY'],
            project_root="/data/git/pillar/pillar",
        )
        handle_exceptions(self)

        bs_handler = BugsnagHandler()
        bs_handler.setLevel(logging.ERROR)
        self.log.addHandler(bs_handler)

    def _config_google_cloud_storage(self):
        # Google Cloud project
        try:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = \
                self.config['GCLOUD_APP_CREDENTIALS']
        except KeyError:
            raise SystemExit('GCLOUD_APP_CREDENTIALS configuration is missing')

        # Storage backend (GCS)
        try:
            os.environ['GCLOUD_PROJECT'] = self.config['GCLOUD_PROJECT']
        except KeyError:
            raise SystemExit('GCLOUD_PROJECT configuration value is missing')

    def _config_algolia(self):
        # Algolia search
        if self.config['SEARCH_BACKEND'] != 'algolia':
            return

        from algoliasearch import algoliasearch

        client = algoliasearch.Client(self.config['ALGOLIA_USER'],
                                      self.config['ALGOLIA_API_KEY'])
        self.algolia_client = client
        self.algolia_index_users = client.init_index(self.config['ALGOLIA_INDEX_USERS'])
        self.algolia_index_nodes = client.init_index(self.config['ALGOLIA_INDEX_NODES'])

    def _config_encoding_backend(self):
        # Encoding backend
        if self.config['ENCODING_BACKEND'] != 'zencoder':
            self.log.warning('Encoding backend %r not supported, no video encoding possible!',
                             self.config['ENCODING_BACKEND'])
            return

        self.log.info('Setting up video encoding backend %r',
                      self.config['ENCODING_BACKEND'])

        from zencoder import Zencoder
        self.encoding_service_client = Zencoder(self.config['ZENCODER_API_KEY'])

    def _config_caching(self):
        from flask_cache import Cache
        self.cache = Cache(self)

    def load_extension(self, pillar_extension, url_prefix):
        from .extension import PillarExtension

        if not isinstance(pillar_extension, PillarExtension):
            if self.config.get('DEBUG'):
                for cls in type(pillar_extension).mro():
                    self.log.error('class %42r (%i) is %42r (%i): %s',
                                   cls, id(cls), PillarExtension, id(PillarExtension),
                                   cls is PillarExtension)
            raise AssertionError('Extension has wrong type %r' % type(pillar_extension))
        self.log.info('Loading extension %s', pillar_extension.name)

        # Remember this extension, and disallow duplicates.
        if pillar_extension.name in self.pillar_extensions:
            raise ValueError('Extension with name %s already loaded', pillar_extension.name)
        self.pillar_extensions[pillar_extension.name] = pillar_extension

        # Load extension Flask configuration
        for key, value in pillar_extension.flask_config():
            self.config.setdefault(key, value)

        # Load extension blueprint(s)
        for blueprint in pillar_extension.blueprints():
            if blueprint.url_prefix:
                if not url_prefix:
                    # If we registered the extension with url_prefix=None
                    url_prefix = ''
                blueprint_prefix = url_prefix + blueprint.url_prefix
            else:
                blueprint_prefix = url_prefix
            self.register_blueprint(blueprint, url_prefix=blueprint_prefix)

        # Load template paths
        tpath = pillar_extension.template_path
        if tpath:
            self.log.info('Extension %s: adding template path %s',
                          pillar_extension.name, tpath)
            if not os.path.exists(tpath):
                raise ValueError('Template path %s for extension %s does not exist.',
                                 tpath, pillar_extension.name)
            self.pillar_extensions_template_paths.append(tpath)

        # Load extension Eve settings
        eve_settings = pillar_extension.eve_settings()

        if 'DOMAIN' in eve_settings:
            pillar_ext_prefix = pillar_extension.name + '_'
            pillar_url_prefix = pillar_extension.name + '/'
            for key, collection in eve_settings['DOMAIN'].items():
                assert key.startswith(pillar_ext_prefix), \
                    'Eve collection names of %s MUST start with %r' % \
                    (pillar_extension.name, pillar_ext_prefix)
                url = key.replace(pillar_ext_prefix, pillar_url_prefix)

                collection.setdefault('datasource', {}).setdefault('source', key)
                collection.setdefault('url', url)

            self.config['DOMAIN'].update(eve_settings['DOMAIN'])

    def _config_jinja_env(self):
        # Start with the extensions...
        paths_list = [
            jinja2.FileSystemLoader(path)
            for path in reversed(self.pillar_extensions_template_paths)
            ]

        # ...then load Pillar paths.
        pillar_dir = os.path.dirname(os.path.realpath(__file__))
        parent_theme_path = os.path.join(pillar_dir, 'web', 'templates')
        current_path = os.path.join(self.app_root, 'templates')
        paths_list += [
            jinja2.FileSystemLoader(current_path),
            jinja2.FileSystemLoader(parent_theme_path),
            self.jinja_loader
        ]
        # Set up a custom loader, so that Jinja searches for a theme file first
        # in the current theme dir, and if it fails it searches in the default
        # location.
        custom_jinja_loader = jinja2.ChoiceLoader(paths_list)
        self.jinja_loader = custom_jinja_loader

        pillar.web.jinja.setup_jinja_env(self.jinja_env)

    def _config_static_dirs(self):
        # Setup static folder for the instanced app
        self.static_folder = os.path.join(self.app_root, 'static')

        # Setup static folder for Pillar
        pillar_dir = os.path.dirname(os.path.realpath(__file__))
        pillar_static_folder = os.path.join(pillar_dir, 'web', 'static')
        self.register_static_file_endpoint('/static/pillar', 'static_pillar', pillar_static_folder)

        # Setup static folders for extensions
        for name, ext in self.pillar_extensions.items():
            if not ext.static_path:
                continue
            self.register_static_file_endpoint('/static/%s' % name,
                                               'static_%s' % name,
                                               ext.static_path)

    def register_static_file_endpoint(self, url_prefix, endpoint_name, static_folder):
        from pillar.web.staticfile import PillarStaticFile

        view_func = PillarStaticFile.as_view(endpoint_name, static_folder=static_folder)
        self.add_url_rule('%s/<path:filename>' % url_prefix, view_func=view_func)

    def process_extensions(self):
        # Re-initialise Eve after we allowed Pillar submodules to be loaded.
        # EVIL STARTS HERE. It just copies part of the Eve.__init__() method.
        self.set_defaults()
        self.validate_config()
        self.validate_domain_struct()

        self._init_url_rules()
        self._init_media_endpoint()
        self._init_schema_endpoint()

        if self.config['OPLOG'] is True:
            self._init_oplog()

        domain_copy = copy.deepcopy(self.config['DOMAIN'])
        for resource, settings in domain_copy.items():
            self.register_resource(resource, settings)

        self.register_error_handlers()
        # EVIL ENDS HERE. No guarantees, though.

        self.finish_startup()

    def register_error_handlers(self):
        super(PillarServer, self).register_error_handlers()

        # Register error handlers per code.
        for code in (403, 404, 412, 500):
            self.register_error_handler(code, self.pillar_error_handler)

        # Register error handlers per exception.
        from pillarsdk import exceptions as sdk_exceptions

        sdk_handlers = [
            (sdk_exceptions.UnauthorizedAccess, self.handle_sdk_unauth),
            (sdk_exceptions.ForbiddenAccess, self.handle_sdk_forbidden),
            (sdk_exceptions.ResourceNotFound, self.handle_sdk_resource_not_found),
            (sdk_exceptions.ResourceInvalid, self.handle_sdk_resource_invalid),
            (sdk_exceptions.MethodNotAllowed, self.handle_sdk_method_not_allowed),
            (sdk_exceptions.PreconditionFailed, self.handle_sdk_precondition_failed),
        ]

        for (eclass, handler) in sdk_handlers:
            self.register_error_handler(eclass, handler)

    def handle_sdk_unauth(self, error):
        """Global exception handling for pillarsdk UnauthorizedAccess
        Currently the api is fully locked down so we need to constantly
        check for user authorization.
        """

        return flask.redirect(flask.url_for('users.login'))

    def handle_sdk_forbidden(self, error):
        self.log.info('Forwarding ForbiddenAccess exception to client: %s', error, exc_info=True)
        error.code = 403
        return self.pillar_error_handler(error)

    def handle_sdk_resource_not_found(self, error):
        self.log.info('Forwarding ResourceNotFound exception to client: %s', error, exc_info=True)

        content = getattr(error, 'content', None)
        if content:
            try:
                error_content = json.loads(content)
            except ValueError:
                error_content = None

            if error_content and error_content.get('_deleted', False):
                # This document used to exist, but doesn't any more. Let the user know.
                doc_name = error_content.get('name')
                node_type = error_content.get('node_type')
                if node_type:
                    node_type = node_type.replace('_', ' ').title()
                    if doc_name:
                        description = '%s "%s" was deleted.' % (node_type, doc_name)
                    else:
                        description = 'This %s was deleted.' % (node_type, )
                else:
                    if doc_name:
                        description = '"%s" was deleted.' % doc_name
                    else:
                        description = None

                error.description = description

        error.code = 404
        return self.pillar_error_handler(error)

    def handle_sdk_precondition_failed(self, error):
        self.log.info('Forwarding PreconditionFailed exception to client: %s', error)

        error.code = 412
        return self.pillar_error_handler(error)

    def handle_sdk_resource_invalid(self, error):
        self.log.info('Forwarding ResourceInvalid exception to client: %s', error, exc_info=True)

        # Raising a Werkzeug 422 exception doens't work, as Flask turns it into a 500.
        return 'The submitted data could not be validated.', 422

    def handle_sdk_method_not_allowed(self, error):
        """Forwards 405 Method Not Allowed to the client.

        This is actually not fair, as a 405 between Pillar and Pillar-Web
        doesn't imply that the request the client did on Pillar-Web is not
        allowed. However, it does allow us to debug this if it happens, by
        watching for 405s in the browser.
        """
        from flask import request

        self.log.info('Forwarding MethodNotAllowed exception to client: %s', error, exc_info=True)
        self.log.info('HTTP Referer is %r', request.referrer)

        # Raising a Werkzeug 405 exception doens't work, as Flask turns it into a 500.
        return 'The requested HTTP method is not allowed on this URL.', 405

    def pillar_error_handler(self, error_ob):

        # 'error_ob' can be any exception. If it's not a Werkzeug exception,
        # handle it as a 500.
        if not hasattr(error_ob, 'code'):
            error_ob.code = 500
        if not hasattr(error_ob, 'description'):
            error_ob.description = str(error_ob)

        if request.full_path.startswith('/%s/' % self.config['URL_PREFIX']):
            from pillar.api.utils import jsonify
            # This is an API request, so respond in JSON.
            return jsonify({
                '_status': 'ERR',
                '_code': error_ob.code,
                '_message': error_ob.description,
            }, status=error_ob.code)

        # See whether we should return an embedded page or a regular one.
        if request.is_xhr:
            fname = 'errors/%i_embed.html' % error_ob.code
        else:
            fname = 'errors/%i.html' % error_ob.code

        # Also handle the case where we didn't create a template for this error.
        try:
            return render_template(fname, description=error_ob.description), error_ob.code
        except TemplateNotFound:
            self.log.warning('Error template %s for code %i not found',
                             fname, error_ob.code)
            return render_template('errors/500.html'), error_ob.code

    def finish_startup(self):
        self.log.info('Using MongoDB database %r', self.config['MONGO_DBNAME'])

        api.setup_app(self)
        web.setup_app(self)
        authentication.setup_app(self)

        for ext in self.pillar_extensions.values():
            self.log.info('Setting up extension %s', ext.name)
            ext.setup_app(self)

        self._config_jinja_env()
        self._config_static_dirs()

        # Only enable this when debugging.
        # self._list_routes()

    def setup_db_indices(self):
        """Adds missing database indices.

        This does NOT drop and recreate existing indices,
        nor does it reconfigure existing indices.
        If you want that, drop them manually first.
        """

        self.log.debug('Adding any missing database indices.')

        import pymongo

        db = self.data.driver.db

        coll = db['tokens']
        coll.create_index([('user', pymongo.ASCENDING)])
        coll.create_index([('token', pymongo.ASCENDING)])

        coll = db['notifications']
        coll.create_index([('user', pymongo.ASCENDING)])

        coll = db['activities-subscriptions']
        coll.create_index([('context_object', pymongo.ASCENDING)])

        coll = db['nodes']
        # This index is used for queries on project, and for queries on
        # the combination (project, node type).
        coll.create_index([('project', pymongo.ASCENDING),
                           ('node_type', pymongo.ASCENDING)])
        coll.create_index([('parent', pymongo.ASCENDING)])
        coll.create_index([('short_code', pymongo.ASCENDING)],
                          sparse=True, unique=True)

    def register_api_blueprint(self, blueprint, url_prefix):
        # TODO: use Eve config variable instead of hard-coded '/api'
        self.register_blueprint(blueprint, url_prefix='/api' + url_prefix)

    def make_header(self, username, subclient_id=''):
        """Returns a Basic HTTP Authentication header value."""
        import base64

        return 'basic ' + base64.b64encode('%s:%s' % (username, subclient_id))

    def post_internal(self, resource, payl=None, skip_validation=False):
        """Workaround for Eve issue https://github.com/nicolaiarocci/eve/issues/810"""
        from eve.methods.post import post_internal

        with self.test_request_context(method='POST', path='%s/%s' % (self.api_prefix, resource)):
            return post_internal(resource, payl=payl, skip_validation=skip_validation)

    def put_internal(self, resource, payload=None, concurrency_check=False,
                     skip_validation=False, **lookup):
        """Workaround for Eve issue https://github.com/nicolaiarocci/eve/issues/810"""
        from eve.methods.put import put_internal

        path = '%s/%s/%s' % (self.api_prefix, resource, lookup['_id'])
        with self.test_request_context(method='PUT', path=path):
            return put_internal(resource, payload=payload, concurrency_check=concurrency_check,
                                skip_validation=skip_validation, **lookup)

    def patch_internal(self, resource, payload=None, concurrency_check=False,
                       skip_validation=False, **lookup):
        """Workaround for Eve issue https://github.com/nicolaiarocci/eve/issues/810"""
        from eve.methods.patch import patch_internal

        path = '%s/%s/%s' % (self.api_prefix, resource, lookup['_id'])
        with self.test_request_context(method='PATCH', path=path):
            return patch_internal(resource, payload=payload, concurrency_check=concurrency_check,
                                  skip_validation=skip_validation, **lookup)

    def _list_routes(self):
        from pprint import pprint
        from flask import url_for

        def has_no_empty_params(rule):
            defaults = rule.defaults if rule.defaults is not None else ()
            arguments = rule.arguments if rule.arguments is not None else ()
            return len(defaults) >= len(arguments)

        links = []
        with self.test_request_context():
            for rule in self.url_map.iter_rules():
                # Filter out rules we can't navigate to in a browser
                # and rules that require parameters
                if "GET" in rule.methods and has_no_empty_params(rule):
                    url = url_for(rule.endpoint, **(rule.defaults or {}))
                    links.append((url, rule.endpoint))

        links.sort(key=lambda t: len(t[0]) + 100 * ('/api/' in t[0]))

        pprint(links)

    def db(self, collection_name: str=None) \
            -> typing.Union[pymongo.collection.Collection, pymongo.database.Database]:
        """Returns the MongoDB database, or the collection (if given)"""

        if collection_name:
            return self.data.driver.db[collection_name]
        return self.data.driver.db

    def extension_sidebar_links(self, project):
        """Returns the sidebar links for the given projects.

        :returns: HTML as a string for the sidebar.
        """

        if not project:
            return ''

        return jinja2.Markup(''.join(ext.sidebar_links(project)
                                     for ext in self.pillar_extensions.values()))
