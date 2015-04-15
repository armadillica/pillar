import os

from eve import Eve

# import random
# import string

from eve.auth import TokenAuth
from eve.auth import BasicAuth
from eve.io.mongo import Validator
from eve.methods.post import post_internal
from bson import ObjectId

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


class TokensAuth(TokenAuth):
    def check_auth(self, token, allowed_roles, resource, method):
        if not token:
            return False
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
                        'firstname': tmpname,
                        'lastname': tmpname,
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
        else:
            return True
        return validation['valid']
        """
        users = app.data.driver.db['users']
        lookup = {'firstname': token['username']}
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
            if properties[prop] == '':
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
        except:
            print ("Error converting")
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
    post_internal(entry, data)


app = Eve(validator=ValidateCustomFields, auth=CustomTokenAuth)
