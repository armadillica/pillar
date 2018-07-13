import logging

from bson import ObjectId, tz_util
from datetime import datetime
import cerberus.errors
from eve.io.mongo import Validator
from flask import current_app

import pillar.markdown

log = logging.getLogger(__name__)


class ValidateCustomFields(Validator):
    # TODO: split this into a convert_property(property, schema) and call that from this function.
    def convert_properties(self, properties, node_schema):
        """Converts datetime strings and ObjectId strings to actual Python objects."""

        date_format = current_app.config['RFC1123_DATE_FORMAT']

        for prop in node_schema:
            if prop not in properties:
                continue
            schema_prop = node_schema[prop]
            prop_type = schema_prop['type']

            if prop_type == 'dict':
                try:
                    dict_valueschema = schema_prop['schema']
                    properties[prop] = self.convert_properties(properties[prop], dict_valueschema)
                except KeyError:
                    dict_valueschema = schema_prop['valueschema']
                    self.convert_dict_values(properties[prop], dict_valueschema)

            elif prop_type == 'list':
                if properties[prop] in ['', '[]']:
                    properties[prop] = []
                if 'schema' in schema_prop:
                    for k, val in enumerate(properties[prop]):
                        item_schema = {'item': schema_prop['schema']}
                        item_prop = {'item': properties[prop][k]}
                        properties[prop][k] = self.convert_properties(
                            item_prop, item_schema)['item']

            # Convert datetime string to RFC1123 datetime
            elif prop_type == 'datetime':
                prop_val = properties[prop]
                prop_naieve = datetime.strptime(prop_val, date_format)
                prop_aware = prop_naieve.replace(tzinfo=tz_util.utc)
                properties[prop] = prop_aware

            elif prop_type == 'objectid':
                prop_val = properties[prop]
                if prop_val:
                    properties[prop] = ObjectId(prop_val)
                else:
                    properties[prop] = None

        return properties

    def convert_dict_values(self, dict_property, dict_valueschema):
        """Calls convert_properties() for the values in the dict.

        Only validates the dict values, not the keys. Modifies the given dict in-place.
        """

        assert dict_valueschema['type'] == 'dict'
        assert isinstance(dict_property, dict)

        for key, val in dict_property.items():
            item_schema = {'item': dict_valueschema}
            item_prop = {'item': val}
            dict_property[key] = self.convert_properties(item_prop, item_schema)['item']

    def _validate_valid_properties(self, valid_properties, field, value):
        """Fake property that triggers node dynamic property validation.

        The rule's arguments are validated against this schema:
        {'type': 'boolean'}
        """
        from pillar.api.utils import project_get_node_type

        projects_collection = current_app.data.driver.db['projects']
        lookup = {'_id': ObjectId(self.document['project'])}

        project = projects_collection.find_one(lookup, {
            'node_types.name': 1,
            'node_types.dyn_schema': 1,
        })
        if project is None:
            log.warning('Unknown project %s, declared by node %s',
                        lookup, self.document.get('_id'))
            self._error(field, 'Unknown project')
            return False

        node_type_name = self.document['node_type']
        node_type = project_get_node_type(project, node_type_name)
        if node_type is None:
            log.warning('Project %s has no node type %s, declared by node %s',
                        project, node_type_name, self.document.get('_id'))
            self._error(field, 'Unknown node type')
            return False

        try:
            value = self.convert_properties(value, node_type['dyn_schema']['shema'])
        except Exception as e:
            log.warning("Error converting form properties", exc_info=True)

        v = self.__class__(schema=node_type['dyn_schema'])
        val = v.validate(value)

        if val:
            # This ensures the modifications made by v's coercion rules are
            # visible to this validator's output.
            #self.current[field] = v.current
            print('*********')
            print(valid_properties)
            #print(v.current)
            return True

        log.warning('Error validating properties for node %s: %s', self.document, v.errors)
        self._error(field, "Error validating properties")

    def _validate_required_after_creation(self, required_after_creation, field, value):
        """Makes a value required after creation only.

        Combine "required_after_creation=True" with "required=False" to allow
        pre-insert hooks to set default values.

        The rule's arguments are validated against this schema:
        {'type': 'boolean'}
        """

        if not required_after_creation:
            # Setting required_after_creation=False is the same as not mentioning this
            # validator at all.
            return

        if self._id is None:
            # This is a creation call, in which case this validator shouldn't run.
            return

        if not value:
            self._error(field, "Value is required once the document was created")

    def _validate_type_iprange(self, field_name: str, value: str):
        """Ensure the field contains a valid IP address.

        Supports both IPv6 and IPv4 ranges. Requires the IPy module.
        """

        from IPy import IP

        try:
            ip = IP(value, make_net=True)
        except ValueError as ex:
            self._error(field_name, str(ex))
            return

        if ip.prefixlen() == 0:
            self._error(field_name, 'Zero-length prefix is not allowed')

    # def _validate_coerce(self, coerce, field: str, value):
    #     """Override Cerberus' _validate_coerce method for richer features.
    #
    #     This now supports named coercion functions (available in Cerberus 1.0+)
    #     and passes the field name to coercion functions as well.
    #     """
    #     if isinstance(coerce, str):
    #         coerce = getattr(self, f'_normalize_coerce_{coerce}')
    #
    #     try:
    #         return coerce(field, value)
    #     except (TypeError, ValueError):
    #         self._error(field, cerberus.errors.ERROR_COERCION_FAILED.format(field))

    def _validator_markdown(self, field, value):
        """This is a placeholder.

        Markdown is actually processed in a hook
        """
        return value


if __name__ == '__main__':
    from pprint import pprint

    v = ValidateCustomFields()
    v.schema = {
        'foo': {'type': 'string', 'validator': 'markdown'},
        'foo_html': {'type': 'string'},
        'nested': {
            'type': 'dict',
            'schema': {
                'bar': {'type': 'string', 'validator': 'markdown'},
                'bar_html': {'type': 'string'},
            }
        }
    }
    print('Valid   :', v.validate({
        'foo': '# Title\n\nHeyyyy',
        'nested': {'bar': 'bhahaha'},
    }))
    print('Document:')
    pprint(v.document)
    print('Errors  :', v.errors)
