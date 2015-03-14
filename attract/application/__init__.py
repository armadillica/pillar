from eve import Eve

import random
import string

from eve.auth import TokenAuth
from eve.auth import BasicAuth
from eve.io.mongo import Validator
from bson import ObjectId


class TokensAuth(TokenAuth):
    def check_auth(self, token, allowed_roles, resource, method):
        tokens = app.data.driver.db['tokens']
        lookup = {'token': token}
        token = tokens.find_one(lookup)
        if not token:
            return False
        users = app.data.driver.db['users']
        lookup = {'firstname': token['username']}
        if allowed_roles:
            lookup['role'] = {'$in': allowed_roles}
        user = users.find_one(lookup)
        if not user:
            return False
        return token

class BasicsAuth(BasicAuth):
    def check_auth(self, username, password, allowed_roles, resource, method):
        return username == 'admin' and password == 'secret'


class MyTokenAuth(BasicsAuth):
    def __init__(self):
        self.token_auth = TokensAuth()
        self.authorized_protected = BasicsAuth.authorized

    def authorized(self, allowed_roles, resource, method):
        if resource=='tokens':
            return self.authorized_protected(self, allowed_roles, resource, method)
        else:
            return self.token_auth.authorized(allowed_roles, resource, method)

    def authorized_protected(self):
        pass


class ValidateCustomFields(Validator):
    def _validate_valid_properties(self, valid_properties, field, value):
        node_types = app.data.driver.db['node_types']
        lookup = {}
        lookup['_id'] = ObjectId(self.document['node_type'])
        node_type = node_types.find_one(lookup)

        v = Validator(node_type['dyn_schema'])
        val = v.validate(value)
        if val:
            return True
        else:
            self._error(field, "Must be hi")


def add_token(documents):
    # Don't use this in production:
    # You should at least make sure that the token is unique.
    # print ("Adding Token")
    for document in documents:
        document["token"] = (''.join(random.choice(string.ascii_uppercase)
                                     for x in range(10)))


app = Eve(validator=ValidateCustomFields, auth=MyTokenAuth)
app.on_insert_tokens += add_token
