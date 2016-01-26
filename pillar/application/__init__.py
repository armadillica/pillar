import os
import json
from bson import ObjectId
from datetime import datetime
import bugsnag
from bugsnag.flask import handle_exceptions
from flask import g
from flask import request
from flask import url_for
from flask import abort
from eve import Eve
from eve.auth import TokenAuth
from eve.io.mongo import Validator

RFC1123_DATE_FORMAT = '%a, %d %b %Y %H:%M:%S GMT'

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
        projects_collection = app.data.driver.db['projects']
        lookup = {'_id': ObjectId(self.document['project'])}
        project = projects_collection.find_one(lookup)
        node_type = next(
            (item for item in project['node_types'] if item.get('name') \
                and item['name'] == self.document['node_type']), None)
        try:
            value = self.convert_properties(value, node_type['dyn_schema'])
        except Exception, e:
            print ("Error converting: {0}".format(e))

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

# We specify a settings.py file because when running on wsgi we can't detect it
# automatically. The default path (which works in Docker) can be overriden with
# an env variable.
settings_path = os.environ.get('EVE_SETTINGS', '/data/git/pillar/pillar/settings.py')
app = Eve(settings=settings_path, validator=ValidateCustomFields, auth=NewAuth)

import config
app.config.from_object(config.Deployment)

bugsnag.configure(
  api_key = app.config['BUGSNAG_API_KEY'],
  project_root = "/data/git/pillar/pillar",
)
handle_exceptions(app)

from application.utils.authentication import validate_token
from application.utils.authorization import check_permissions
from application.utils.cdn import hash_file_path
from application.utils.gcs import GoogleCloudStorageBucket
from application.utils.gcs import update_file_name


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

def project_node_type_has_method(response):
    """Check for a specific request arg, and check generate the allowed_methods
    list for the required node_type.
    """
    try:
        node_type_name = request.args['node_type']
    except KeyError:
        return
    # Proceed only node_type has been requested
    if node_type_name:
        # Look up the node type in the project document
        node_type = next(
            (item for item in response['node_types'] if item.get('name') \
                and item['name'] == node_type_name), None)
        if not node_type:
            return abort(404)
        # Check permissions and append the allowed_methods to the node_type
        if not check_permissions(node_type, 'GET', append_allowed_methods=True):
            return abort(403)


app.on_fetched_item_nodes += before_returning_item_permissions
app.on_fetched_item_nodes += item_parse_attachments
app.on_fetched_resource_nodes += before_returning_resource_permissions
app.on_fetched_resource_nodes += resource_parse_attachments
app.on_fetched_item_node_types += before_returning_item_permissions
app.on_fetched_resource_node_types += before_returning_resource_permissions
app.on_replace_nodes += before_replacing_node
app.on_insert_nodes += before_inserting_nodes
app.on_fetched_item_projects += before_returning_item_permissions
app.on_fetched_item_projects += project_node_type_has_method
app.on_fetched_resource_projects += before_returning_resource_permissions

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
