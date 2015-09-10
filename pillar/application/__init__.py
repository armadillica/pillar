import os
import json

from eve import Eve

# import random
# import string

from eve.auth import TokenAuth
from eve.auth import BasicAuth
from eve.io.mongo import Validator
from eve.methods.post import post_internal
from bson import ObjectId

from flask import g
from flask import request
from flask import url_for

from pre_hooks import pre_GET
from pre_hooks import pre_PUT
from pre_hooks import pre_PATCH
from pre_hooks import pre_POST
from pre_hooks import pre_DELETE
from pre_hooks import check_permissions
from pre_hooks import compute_permissions

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
    """Validate a Token against Blender ID server
    """
    import requests
    payload = dict(
        token=token)
    try:
        r = requests.post("{0}/u/validate_token".format(
            SystemUtility.blender_id_endpoint()), data=payload)
    except requests.exceptions.ConnectionError as e:
        raise e

    if r.status_code == 200:
        message = r.json()['message']
        valid = r.json()['valid']
        user = r.json()['user']
    else:
        message = ""
        valid = False
        user = None
    return dict(valid=valid, message=message, user=user)


def validate_token():
    token = request.authorization.username
    tokens = app.data.driver.db['tokens']
    users = app.data.driver.db['users']
    lookup = {'token': token, 'expire_time': {"$gt": datetime.now()}}
    dbtoken = tokens.find_one(lookup)
    if not dbtoken:
        validation = validate(token)
        if validation['valid']:
            email = validation['user']['email']
            dbuser = users.find_one({'email': email})
            tmpname = email.split('@')[0]
            if not dbuser:
                user_data = {
                    'first_name': tmpname,
                    'last_name': tmpname,
                    'email': email,
                    'role': ['admin'],
                }
                r = post_internal('users', user_data)
                user_id = r[0]["_id"]
            else:
                user_id = dbuser['_id']

            token_data = {
                'user': user_id,
                'token': token,
                'expire_time': datetime.now() + timedelta(hours=1)
            }
            post_internal('tokens', token_data)
            return token_data
        else:
            return None
    else:
        token_data = {
            'user': dbtoken['user'],
            'token': dbtoken['token'],
            'expire_time': dbtoken['expire_time']
        }
        return token_data


class TokensAuth(TokenAuth):

    def check_auth(self, token, allowed_roles, resource, method):
        if not token:
            return False

        validate_token()

        # if dbtoken:
        #     check_permissions(dbtoken['user'])
        #     return True

        # return validation['valid']
        return True
        """
        users = app.data.driver.db['users']
        lookup = {'first_name': token['username']}
        if allowed_roles:
            lookup['role'] = {'$in': allowed_roles}
        user = users.find_one(lookup)
        if not user:
            return False
        return token
        """


class BasicsAuth(BasicAuth):
    def check_auth(self, username, password, allowed_roles, resource, method):
        # return username == 'admin' and password == 'secret'
        return True


class CustomTokenAuth(BasicsAuth):
    """Switch between Basic and Token auth"""
    def __init__(self):
        self.token_auth = TokensAuth()
        self.authorized_protected = BasicsAuth.authorized

    def authorized(self, allowed_roles, resource, method):
        # if resource == 'tokens':
        if False:
            return self.authorized_protected(
                self, allowed_roles, resource, method)
        else:
            return self.token_auth.authorized(allowed_roles, resource, method)

    def authorized_protected(self):
        pass

def convert_properties(properties, node_schema):
    for prop in node_schema:
        if not prop in properties:
            continue
        schema_prop = node_schema[prop]
        prop_type = schema_prop['type']
        if prop_type == 'dict':
            properties[prop] = convert_properties(
                properties[prop], schema_prop['schema'])
        if prop_type == 'list':
            if properties[prop] in ['', '[]']:
                properties[prop] = []
            for k, val in enumerate(properties[prop]):
                if not 'schema' in schema_prop:
                    continue
                item_schema = {'item': schema_prop['schema']}
                item_prop = {'item': properties[prop][k]}
                properties[prop][k] = convert_properties(
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


class ValidateCustomFields(Validator):
    def _validate_valid_properties(self, valid_properties, field, value):
        node_types = app.data.driver.db['node_types']
        lookup = {}
        lookup['_id'] = ObjectId(self.document['node_type'])
        node_type = node_types.find_one(lookup)

        try:
            value = convert_properties(value, node_type['dyn_schema'])
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


app = Eve(validator=ValidateCustomFields, auth=CustomTokenAuth)

import config
app.config.from_object(config.Deployment)

def global_validation():
    setattr(g, 'token_data', validate_token())
    setattr(g, 'validate', validate(g.get('token_data')['token']))
    check_permissions(g.get('token_data')['user'], app.data.driver)


def pre_GET_nodes(request, lookup):
    # Only get allowed documents
    global_validation()
    # print ("Get")
    # print ("Owner: {0}".format(g.get('owner_permissions')))
    # print ("World: {0}".format(g.get('world_permissions')))
    return pre_GET(request, lookup, app.data.driver)


def pre_PUT_nodes(request, lookup):
    # Only Update allowed documents
    global_validation()
    # print ("Put")
    # print ("Owner: {0}".format(g.get('owner_permissions')))
    # print ("World: {0}".format(g.get('world_permissions')))
    return pre_PUT(request, lookup, app.data.driver)


def pre_PATCH_nodes(request):
    return pre_PATCH(request, app.data.driver)


def pre_POST_nodes(request):
    global_validation()
    # print ("Post")
    # print ("World: {0}".format(g.get('world_permissions')))
    # print ("Group: {0}".format(g.get('groups_permissions')))
    return pre_POST(request, app.data.driver)


def pre_DELETE_nodes(request, lookup):
    # Only Delete allowed documents
    global_validation()
    # print ("Delete")
    # print ("Owner: {0}".format(type_owner_permissions))
    # print ("World: {0}".format(type_world_permissions))
    # print ("Groups: {0}".format(type_groups_permissions))
    return pre_DELETE(request, lookup, app.data.driver)


app.on_pre_GET_nodes += pre_GET_nodes
app.on_pre_POST_nodes += pre_POST_nodes
app.on_pre_PATCH_nodes += pre_PATCH_nodes
app.on_pre_PUT_nodes += pre_PUT_nodes
app.on_pre_DELETE_nodes += pre_DELETE_nodes


def post_GET_user(request, payload):
    json_data = json.loads(payload.data)
    # Check if we are querying the users endpoint (instead of the single user)
    if json_data.get('_id') is None:
        return
    json_data['computed_permissions'] = \
        compute_permissions(json_data['_id'], app.data.driver)
    payload.data = json.dumps(json_data)


app.on_post_GET_users += post_GET_user

from utils import hash_file_path
# Hook to check the backend of a file resource, to build an appropriate link
# that can be used by the client to retrieve the actual file.
def generate_link(backend, path):
    if backend == 'pillar':
        link = url_for('file_server.index', file_name=path, _external=True)
    elif backend == 'cdnsun':
        link = hash_file_path(path, None)
    else:
        link = None
    return link

def before_returning_file(response):
    response['link'] = generate_link(response['backend'], response['path'])

def before_returning_files(response):
    for item in response['_items']:
        item['link'] = generate_link(item['backend'], item['path'])


app.on_fetched_item_files += before_returning_file
app.on_fetched_resource_files += before_returning_files

# The file_server module needs app to be defined
from file_server import file_server
app.register_blueprint(file_server, url_prefix='/file_server')
