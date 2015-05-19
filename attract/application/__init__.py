import os

from eve import Eve

# import random
# import string
import json

from eve.auth import TokenAuth
from eve.auth import BasicAuth
from eve.io.mongo import Validator
from eve.methods.post import post_internal
from bson import ObjectId

from flask import g
from flask import abort
from flask import request

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


def global_validation():
    setattr(g, 'token_data', validate_token())
    setattr(g, 'validate', validate(g.get('token_data')['token']))
    check_permissions(g.get('token_data')['user'])


def permissions_lookup(action, lookup):
    type_world_permissions = g.get('type_world_permissions')
    type_owner_permissions = g.get('type_owner_permissions')
    node_types = []
    # Get all node_types allowed by world:
    for per in type_world_permissions:
        if action in type_world_permissions[per]:
            node_types.append(str(per))
    # Get all nodes with node_type allowed by owner if user == owner
    owner_lookup = []
    for per in type_owner_permissions:
        if action in type_owner_permissions[per]:
            if action not in type_world_permissions[per]:
                # If one of the following is true
                # If node_type==node_type and user==user
                owner_lookup.append(
                    {'$and': [{'node_type': str(per)},
                              {'user': str(g.get('token_data')['user'])}]})
    lookup['$or'] = [{'node_type': {'$in': node_types}}]
    if len(owner_lookup) > 0:
        lookup['$or'].append({'$or': owner_lookup})
    return lookup


def pre_GET(request, lookup):
    # Only get allowed documents
    global_validation()
    # print ("Get")
    # print ("Owner: {0}".format(g.get('owner_permissions')))
    # print ("World: {0}".format(g.get('world_permissions')))
    action = 'GET'
    if 'token_type' not in lookup and '_id' not in request.view_args:
        # Is quering for all nodes (mixed types)
        lookup = permissions_lookup(action, lookup)
    else:
        # Is quering for one specific node
        if action not in g.get('world_permissions') and \
                action not in g.get('groups_permissions'):
            lookup['user'] = g.get('token_data')['user']
    # token_data = validate_token()
    # validate(token_data['token'])

    # lookup["userr"] = "user"
    # print ("Lookup")
    # print (lookup)


def pre_PUT(request, lookup):
    # Only Update allowed documents
    global_validation()
    # print ("Put")
    # print ("Owner: {0}".format(g.get('owner_permissions')))
    # print ("World: {0}".format(g.get('world_permissions')))
    action = 'UPDATE'
    if 'token_type' not in lookup and '_id' not in request.view_args:
        # Is updating all nodes (mixed types)
        lookup = permissions_lookup(action, lookup)
    else:
        # Is updating one specific node
        if action not in g.get('world_permissions') and \
                action not in g.get('groups_permissions'):
            lookup['user'] = g.get('token_data')['user']

    # print ("Lookup")
    # print (lookup)


def pre_PATCH(request, lookup):
    print ("Patch")


def pre_POST(request):
    # Only Post allowed documents
    global_validation()
    # print ("Post")
    # print ("World: {0}".format(g.get('world_permissions')))
    # print ("Group: {0}".format(g.get('groups_permissions')))
    action = 'POST'
    print (g.get('type_groups_permissions'))
    # Is quering for one specific node
    if action not in g.get('world_permissions') and \
            action not in g.get('groups_permissions'):
        abort(403)


def pre_DELETE(request, lookup):
    # Only Delete allowed documents
    global_validation()
    type_world_permissions = g.get('type_world_permissions')
    type_owner_permissions = g.get('type_owner_permissions')
    type_groups_permissions = g.get('type_groups_permissions')
    # print ("Delete")
    print ("Owner: {0}".format(type_owner_permissions))
    print ("World: {0}".format(type_world_permissions))
    print ("Groups: {0}".format(type_groups_permissions))
    action = 'DELETE'

    if '_id' in lookup:
        nodes = app.data.driver.db['nodes']
        dbnode = nodes.find_one({'_id': ObjectId(lookup['_id'])})
        # print (dbnode.count())
        node_type = dbnode['node_type']
        if g.get('token_data')['user'] == dbnode['user']:
            owner = True
        else:
            owner = False
        if action not in type_world_permissions[node_type] and \
            action not in type_groups_permissions[node_type]:
            if action not in type_owner_permissions[node_type]:
                print ("Abort1")
                abort(403)
            else:
                if not owner:
                    print ("Abort2")
                    abort(403)
    else:
        print ("Abort3")
        abort(403)


def check_permissions(user):
    node_type = None
    dbnode = None
    owner_permissions = []
    world_permissions = []
    groups_permissions = []
    groups = app.data.driver.db['groups']
    users = app.data.driver.db['users']
    owner_group = groups.find_one({'name': 'owner'})
    world_group = groups.find_one({'name': 'world'})
    user_data = users.find_one({'_id': ObjectId(user)})
    # Entry point should be nodes
    entry_point = request.path.split("/")[1]
    if entry_point != 'nodes':
        return
    # If is requesting a specific node
    try:
        uuid = request.path.split("/")[2]
        nodes = app.data.driver.db['nodes']
        lookup = {'_id': ObjectId(uuid)}
        dbnode = nodes.find_one(lookup)
    except IndexError:
        pass
    if dbnode:
        node_type = str(dbnode['node_type'])

    json_data = None
    try:
        json_data = json.loads(request.data)
    except ValueError:
        pass
    if not node_type and json_data:
        if 'node_type' in json_data:
            node_type = json_data['node_type']

    # Extract query lookup
    # which node_type is asking for?
    for arg in request.args:
        if arg == 'where':
            try:
                where = json.loads(request.args[arg])
            except ValueError:
                raise
            if where.get('node_type'):
                node_type = where.get('node_type')
            break

    # Get and store permissions for that node_type
    type_owner_permissions = {}
    type_world_permissions = {}
    type_groups_permissions = {}

    for per in owner_group['permissions']:
        type_owner_permissions[per['node_type']] = per['permissions']
        if str(per['node_type']) == node_type:
            owner_permissions = per['permissions']

    for per in world_group['permissions']:
        type_world_permissions[per['node_type']] = per['permissions']
        if str(per['node_type']) == node_type:
            world_permissions = per['permissions']

        # Adding empty permissions
        if per['node_type'] not in type_groups_permissions:
            type_groups_permissions[per['node_type']] = []

    groups_data = user_data.get('groups')
    if groups_data:
        for group in groups_data:
            group_data = groups.find_one({'_id': ObjectId(group)})
            for per in group_data['permissions']:
                type_groups_permissions[per['node_type']] += \
                    per['permissions']
                if str(per['node_type']) == node_type:
                    groups_permissions = per['permissions']

    # Store permission properties on global
    setattr(g, 'owner_permissions', owner_permissions)
    setattr(g, 'world_permissions', world_permissions)
    setattr(g, 'groups_permissions', groups_permissions)
    setattr(g, 'type_owner_permissions', type_owner_permissions)
    setattr(g, 'type_world_permissions', type_world_permissions)
    setattr(g, 'type_groups_permissions', type_groups_permissions)


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
            properties[prop] = ObjectId(prop_val)
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
        print (value)

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
app.on_pre_GET_nodes += pre_GET
app.on_pre_POST_nodes += pre_POST
app.on_pre_PATCH_nodes += pre_PATCH
app.on_pre_PUT_nodes += pre_PUT
app.on_pre_DELETE_nodes += pre_DELETE

# The file_server module needs app to be defined
from file_server import file_server
app.register_blueprint(file_server, url_prefix='/file_server')
