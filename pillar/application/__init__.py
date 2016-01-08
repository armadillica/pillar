import os
import json
import requests
import bugsnag
from bugsnag.flask import handle_exceptions
from eve import Eve
from pymongo import MongoClient
from eve.auth import TokenAuth
from eve.auth import BasicAuth
from eve.io.mongo import Validator
from eve.methods.post import post_internal
from bson import ObjectId

from flask import g
from flask import request
from flask import url_for
from flask import abort


from datetime import datetime
from datetime import timedelta


RFC1123_DATE_FORMAT = '%a, %d %b %Y %H:%M:%S GMT'


class SystemUtility():
    def __new__(cls, *args, **kwargs):
        raise TypeError("Base class may not be instantiated")

    @staticmethod
    def blender_id_endpoint():
        """Gets the endpoint for the authentication API. If the env variable
        is defined, it's possible to override the (default) production address.
        """
        return os.environ.get(
            'BLENDER_ID_ENDPOINT', "https://www.blender.org/id")


def validate(token):
    """Validate a token against the Blender ID server. This simple lookup
    returns a dictionary with the following keys:

    - message: a success message
    - valid: a boolean, stating if the token is valid
    - user: a dictionary with information regarding the user
    """
    payload = dict(
        token=token)
    try:
        r = requests.post("{0}/u/validate_token".format(
            SystemUtility.blender_id_endpoint()), data=payload)
    except requests.exceptions.ConnectionError as e:
        raise e

    if r.status_code == 200:
        response = r.json()
    else:
        response = None
    return response


def validate_token():
    """Validate the token provided in the request and populate the current_user
    flask.g object, so that permissions and access to a resource can be defined
    from it.
    """
    if not request.authorization:
        # If no authorization headers are provided, we are getting a request
        # from a non logged in user. Proceed accordingly.
        return None

    current_user = {}

    token = request.authorization.username
    tokens_collection = app.data.driver.db['tokens']

    lookup = {'token': token, 'expire_time': {"$gt": datetime.now()}}
    db_token = tokens_collection.find_one(lookup)
    if not db_token:
        # If no valid token is found, we issue a new request to the Blender ID
        # to verify the validity of the token. We will get basic user info if
        # the user is authorized and we will make a new token.
        validation = validate(token)
        if validation['status'] == 'success':
            users = app.data.driver.db['users']
            email = validation['data']['user']['email']
            db_user = users.find_one({'email': email})
            # Ensure unique username
            username = email.split('@')[0]
            def make_unique_username(username, index=1):
                """Ensure uniqueness of a username by appending an incremental
                digit at the end of it.
                """
                user_from_username = users.find_one({'username': username})
                if user_from_username:
                    if index > 1:
                        index += 1
                        username = username[:-1]
                    username = "{0}{1}".format(username, index)
                    return make_unique_username(username, index=index)
                return username
            # Check for min length of username (otherwise validation fails)
            username = "___{0}".format(username) if len(username) < 3 else username
            username = make_unique_username(username)

            full_name = username
            if not db_user:
                user_data = {
                    'full_name': full_name,
                    'username': username,
                    'email': email,
                    'auth': [{
                        'provider': 'blender-id',
                        'user_id': str(validation['data']['user']['id']),
                        'token': ''}],
                    'settings': {
                        'email_communications': 1
                    }
                }
                r = post_internal('users', user_data)
                user_id = r[0]['_id']
                groups = None
            else:
                user_id = db_user['_id']
                groups = db_user['groups']

            token_data = {
                'user': user_id,
                'token': token,
                'expire_time': datetime.now() + timedelta(hours=1)
            }
            post_internal('tokens', token_data)
            current_user = dict(
                user_id=user_id,
                token=token,
                groups=groups,
                token_expire_time=datetime.now() + timedelta(hours=1))
            #return token_data
        else:
            return None
    else:
        users = app.data.driver.db['users']
        db_user = users.find_one(db_token['user'])
        current_user = dict(
            user_id=db_token['user'],
            token=db_token['token'],
            groups=db_user['groups'],
            token_expire_time=db_token['expire_time'])

    setattr(g, 'current_user', current_user)


class NewAuth(TokenAuth):
    def check_auth(self, token, allowed_roles, resource, method):
        if not token:
            return False
        else:
            validate_token()

        return True


class ValidateCustomFields(Validator):
    def convert_properties(self, properties, node_schema):
        for prop in node_schema:
            if not prop in properties:
                continue
            schema_prop = node_schema[prop]
            prop_type = schema_prop['type']
            if prop_type == 'dict':
                properties[prop] = self.convert_properties(
                    properties[prop], schema_prop['schema'])
            if prop_type == 'list':
                if properties[prop] in ['', '[]']:
                    properties[prop] = []
                for k, val in enumerate(properties[prop]):
                    if not 'schema' in schema_prop:
                        continue
                    item_schema = {'item': schema_prop['schema']}
                    item_prop = {'item': properties[prop][k]}
                    properties[prop][k] = self.convert_properties(
                        item_prop, item_schema)['item']
            # Convert datetime string to RFC1123 datetime
            elif prop_type == 'datetime':
                prop_val = properties[prop]
                properties[prop] = datetime.strptime(prop_val, RFC1123_DATE_FORMAT)
            elif prop_type == 'objectid':
                prop_val = properties[prop]
                if prop_val:
                    properties[prop] = ObjectId(prop_val)
                else:
                    properties[prop] = None

        return properties

    def _validate_valid_properties(self, valid_properties, field, value):
        node_types = app.data.driver.db['node_types']
        lookup = {}
        lookup['_id'] = ObjectId(self.document['node_type'])
        node_type = node_types.find_one(lookup)

        try:
            value = self.convert_properties(value, node_type['dyn_schema'])
        except Exception, e:
            print ("Error converting: {0}".format(e))
        #print (value)

        v = Validator(node_type['dyn_schema'])
        val = v.validate(value)

        if val:
            return True
        else:
            try:
                print (val.errors)
            except:
                pass
            self._error(
                field, "Error validating properties")


def post_item(entry, data):
    return post_internal(entry, data)


# We specify a settings.py file because when running on wsgi we can't detect it
# automatically. The default path (which work in Docker) can be overriden with
# an env variable.
settings_path = os.environ.get('EVE_SETTINGS', '/data/git/pillar/pillar/settings.py')
app = Eve(settings=settings_path, validator=ValidateCustomFields, auth=NewAuth)

import config
app.config.from_object(config.Deployment)

client = MongoClient(app.config['MONGO_HOST'], 27017)
db = client.eve
bugsnag.configure(
  api_key = app.config['BUGSNAG_API_KEY'],
  project_root = "/data/git/pillar/pillar",
)
handle_exceptions(app)
from utils.cdn import hash_file_path
from application.utils.gcs import GoogleCloudStorageBucket

def update_file_name(item):
    """Assign to the CGS blob the same name of the asset node. This way when
    downloading an asset we get a human-readable name.
    """

    def _update_name(item, file_id):
        files_collection = app.data.driver.db['files']
        f = files_collection.find_one({'_id': file_id})
        status = item['properties']['status']
        if f and f['backend'] == 'gcs' and status != 'processing':
            # Process only files that are on GCS and that are not processing
            try:
                storage = GoogleCloudStorageBucket(str(item['project']))
                blob = storage.Get(f['file_path'], to_dict=False)
                storage.update_name(blob, "{0}.{1}".format(
                    item['name'], f['format']))
                try:
                    # Assign the same name to variations
                    for v in f['variations']:
                        blob = storage.Get(v['file_path'], to_dict=False)
                        storage.update_name(blob, "{0}-{1}.{2}".format(
                            item['name'], v['size'], v['format']))
                except KeyError:
                    pass
            except AttributeError:
                bugsnag.notify(Exception('Missing or conflicting ids detected'),
                    meta_data={'nodes_info':
                        {'node_id': item['_id'], 'file_id': file_id}})

    # Currently we search for 'file' and 'files' keys in the object properties.
    # This could become a bit more flexible and realy on a true reference of the
    # file object type from the schema.
    if 'file' in item['properties']:
        _update_name(item, item['properties']['file'])

    elif 'files' in item['properties']:
        for f in item['properties']['files']:
            _update_name(item, f['file'])


def check_permissions(resource, method, append_allowed_methods=False):
    """Check user permissions to access a node. We look up node permissions from
    world to groups to users and match them with the computed user permissions.
    If there is not match, we return 403.
    """
    if method != 'GET' and append_allowed_methods:
        raise ValueError("append_allowed_methods only allowed with 'GET' method")

    allowed_methods = []

    current_user = g.get('current_user', None)

    if 'permissions' in resource:
        # If permissions are embedded in the node (this overrides any other
        # matching permission originally set at node_type level)
        resource_permissions = resource['permissions']
    else:
        resource_permissions = None

    if 'node_type' in resource:
        if type(resource['node_type']) is dict:
            # If the node_type is embedded in the document, extract permissions
            # from there
            computed_permissions = resource['node_type']['permissions']
        else:
            # If the node_type is referenced with an ObjectID (was not embedded on
            # request) query for if from the database and get the permissions
            node_types_collection = app.data.driver.db['node_types']
            node_type = node_types_collection.find_one(resource['node_type'])
            computed_permissions = node_type['permissions']
    else:
        computed_permissions = None

    # Override computed_permissions if override is provided
    if resource_permissions and computed_permissions:
        for k, v in resource_permissions.iteritems():
            computed_permissions[k] = v
    elif resource_permissions and not computed_permissions:
        computed_permissions = resource_permissions

    if current_user:
        # If the user is authenticated, proceed to compare the group permissions
        for permission in computed_permissions['groups']:
            if permission['group'] in current_user['groups']:
                allowed_methods += permission['methods']
                if method in permission['methods'] and not append_allowed_methods:
                    return

        for permission in computed_permissions['users']:
            if current_user['user_id'] == permission['user']:
                allowed_methods += permission['methods']
                if method in permission['methods'] and not append_allowed_methods:
                    return

    # Check if the node is public or private. This must be set for non logged
    # in users to see the content. For most BI projects this is on by default,
    # while for private project this will not be set at all.
    if 'world' in computed_permissions:
        allowed_methods += computed_permissions['world']
        if method in computed_permissions['world'] and not append_allowed_methods:
            return

    if append_allowed_methods and method in allowed_methods:
        resource['allowed_methods'] = list(set(allowed_methods))
        return resource

    return None

def before_returning_item_permissions(response):
    # Run validation process, since GET on nodes entry point is public
    validate_token()
    if not check_permissions(response, 'GET', append_allowed_methods=True):
        return abort(403)

def before_returning_resource_permissions(response):
    for item in response['_items']:
        validate_token()
        check_permissions(item, 'GET', append_allowed_methods=True)

def before_replacing_node(item, original):
    check_permissions(original, 'PUT')
    update_file_name(item)

def before_inserting_nodes(items):
    """Before inserting a node in the collection we check if the user is allowed
    and we append the project id to it.
    """
    nodes_collection = app.data.driver.db['nodes']
    def find_parent_project(node):
        """Recursive function that finds the ultimate parent of a node."""
        if node and 'parent' in node:
            parent = nodes_collection.find_one({'_id': node['parent']})
            return find_parent_project(parent)
        if node:
            return node
        else:
            return None
    for item in items:
        check_permissions(item, 'POST')
        if 'parent' in item and 'project' not in item:
            parent = nodes_collection.find_one({'_id': item['parent']})
            project = find_parent_project(parent)
            if project:
                item['project'] = project['_id']

def item_parse_attachments(response):
    """Before returning a response, check if the 'attachments' property is
    defined. If yes, load the file (for the moment only images) in the required
    variation, get the link and build a Markdown representation. Search in the
    'field' specified in the attachmentand replace the 'slug' tag with the
    generated link.
    """
    if 'properties' in response and 'attachments' in response['properties']:
        files_collection = app.data.driver.db['files']
        for field in response['properties']['attachments']:
            for attachment in response['properties']['attachments']:
                # Make a list from the property path
                field_name_path = attachment['field'].split('.')
                # This currently allow to access only properties inside of
                # the properties property
                if len(field_name_path) > 1:
                    field_content = response[field_name_path[0]][field_name_path[1]]
                # This is for the "normal" first level property
                else:
                    field_content = response[field_name_path[0]]
                for f in attachment['files']:
                    slug = f['slug']
                    slug_tag = "[{0}]".format(slug)
                    f = files_collection.find_one({'_id': f['file']})
                    size = f['size'] if 'size' in f else 'l'
                    # Get the correc variation from the file
                    thumbnail = next((item for item in f['variations'] if
                        item['size'] == size), None)
                    l = generate_link(f['backend'], thumbnail['file_path'], str(f['project']))
                    # Build Markdown img string
                    l = '![{0}]({1} "{2}")'.format(slug, l, f['name'])
                    # Parse the content of the file and replace the attachment
                    # tag with the actual image link
                    field_content = field_content.replace(slug_tag, l)
                # Apply the parsed value back to the property. See above for
                # clarifications on how this is done.
                if len(field_name_path) > 1:
                    response[field_name_path[0]][field_name_path[1]] = field_content
                else:
                    response[field_name_path[0]] = field_content

def resource_parse_attachments(response):
    for item in response['_items']:
        item_parse_attachments(item)

app.on_fetched_item_nodes += before_returning_item_permissions
app.on_fetched_item_nodes += item_parse_attachments
app.on_fetched_resource_nodes += before_returning_resource_permissions
app.on_fetched_resource_nodes += resource_parse_attachments
app.on_fetched_item_node_types += before_returning_item_permissions
app.on_fetched_resource_node_types += before_returning_resource_permissions
app.on_replace_nodes += before_replacing_node
app.on_insert_nodes += before_inserting_nodes

def post_GET_user(request, payload):
    json_data = json.loads(payload.data)
    # Check if we are querying the users endpoint (instead of the single user)
    if json_data.get('_id') is None:
        return
    # json_data['computed_permissions'] = \
    #     compute_permissions(json_data['_id'], app.data.driver)
    payload.data = json.dumps(json_data)

app.on_post_GET_users += post_GET_user

from modules.file_storage import process_file
from modules.file_storage import delete_file

def post_POST_files(request, payload):
    """After an file object has been created, we do the necessary processing
    and further update it.
    """
    process_file(request.get_json())

app.on_post_POST_files += post_POST_files


# Hook to check the backend of a file resource, to build an appropriate link
# that can be used by the client to retrieve the actual file.
def generate_link(backend, file_path, project_id=None):
    if backend == 'gcs':
        storage = GoogleCloudStorageBucket(project_id)
        blob = storage.Get(file_path)
        link = None if not blob else blob['signed_url']
    elif backend == 'pillar':
        link = url_for('file_storage.index', file_name=file_path, _external=True,
        _scheme=app.config['SCHEME'])
    elif backend == 'cdnsun':
        link = hash_file_path(file_path, None)
    else:
        link = None
    return link

def before_returning_file(response):
    # TODO: add project id to all files
    project_id = None if 'project' not in response else str(response['project'])
    response['link'] = generate_link(
        response['backend'], response['file_path'], project_id)
    if 'variations' in response:
        for variation in response['variations']:
            variation['link'] = generate_link(
                response['backend'], variation['file_path'], project_id)

def before_returning_files(response):
    for item in response['_items']:
        # TODO: add project id to all files
        project_id = None if 'project' not in item else str(item['project'])
        item['link'] = generate_link(item['backend'], item['file_path'], project_id)


app.on_fetched_item_files += before_returning_file
app.on_fetched_resource_files += before_returning_files


def before_deleting_file(item):
    delete_file(item)

app.on_delete_item_files += before_deleting_file

# The file_storage module needs app to be defined
from modules.file_storage import file_storage
#from modules.file_storage.serve import *
app.register_blueprint(file_storage, url_prefix='/storage')
