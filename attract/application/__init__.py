from eve import Eve
from eve.auth import TokenAuth

import random
import string

from eve.io.mongo import Validator

class ValidateCustomFields(Validator):
    def _validate_valid_properties(self, valid_properties, field, value):
        node_types = app.data.driver.db['ntypes']
        lookup = {}
        lookup['_id'] = self.document['node_type']
        node_type = node_types.find_one(lookup)

        v = Validator(node_type['dyn_schema'])
        val = v.validate(value)
        if val:
            return True
        else:
            self._error(field, "Must be hi")


class RolesAuth(TokenAuth):
    def check_auth(self, token,  allowed_roles, resource, method):
        accounts = app.data.driver.db['users']
        lookup = {'token': token}
        if allowed_roles:
            lookup['role'] = {'$in': allowed_roles}
        account = accounts.find_one(lookup)
        return account


def add_token(documents):
    # Don't use this in production:
    # You should at least make sure that the token is unique.
    for document in documents:
        document["token"] = (''.join(random.choice(string.ascii_uppercase)
                                     for x in range(10)))

app = Eve(validator=ValidateCustomFields, auth=RolesAuth)
app.on_insert_users += add_token

