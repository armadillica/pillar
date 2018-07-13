"""Test that what we feed to Cerberus actually works.

This'll help us upgrade to new versions of Cerberus.
"""

import unittest
from pillar.tests import AbstractPillarTest

from bson import ObjectId


class CerberusCanaryTest(unittest.TestCase):

    def _canary_test(self, validator):
        groups_schema = {'name': {'type': 'string', 'required': True}}

        # On error, validate_schema() raises ValidationError
        if hasattr(validator, 'validate_schema'):
            # It was removed in Cerberus 1.0 (or thereabouts)
            validator.validate_schema(groups_schema)

        # On error, validate() returns False
        self.assertTrue(validator.validate({'name': 'je moeder'}, groups_schema))
        self.assertFalse(validator.validate({'je moeder': 'op je hoofd'}, groups_schema))

    def test_canary(self):
        import cerberus

        validator = cerberus.Validator()
        self._canary_test(validator)

    def test_our_validator_simple(self):
        from pillar.api import custom_field_validation

        validator = custom_field_validation.ValidateCustomFields()
        self._canary_test(validator)


class ValidationTest(AbstractPillarTest):
    def setUp(self):
        super().setUp()

        from pillar.api import custom_field_validation

        self.validator = custom_field_validation.ValidateCustomFields()
        self.user_id = ObjectId(8 * 'abc')
        self.ensure_user_exists(self.user_id, 'Tést Üsâh')

    def assertValid(self, document, schema):
        with self.app.app_context():
            is_valid = self.validator.validate(document, schema)
        self.assertTrue(is_valid, f'errors: {self.validator.errors}')

    def assertInvalid(self, document, schema):
        with self.app.app_context():
            is_valid = self.validator.validate(document, schema)
        self.assertFalse(is_valid)


class ProjectValidationTest(ValidationTest):

    def test_empty(self):
        from pillar.api.eve_settings import projects_schema
        self.assertInvalid({}, projects_schema)

    def test_simple_project(self):
        from pillar.api.eve_settings import projects_schema

        project = {
            'name': 'Té Ærhüs',
            'user': self.user_id,
            'category': 'assets',
            'is_private': False,
            'status': 'published',
        }

        self.assertValid(project, projects_schema)

    def test_with_node_types(self):
        from pillar.api.eve_settings import projects_schema
        from pillar.api import node_types

        project = {
            'name': 'Té Ærhüs',
            'user': self.user_id,
            'category': 'assets',
            'is_private': False,
            'status': 'published',
            'node_types': [node_types.node_type_asset,
                           node_types.node_type_comment]
        }

        self.assertValid(project, projects_schema)


class NodeValidationTest(ValidationTest):
    def setUp(self):
        super().setUp()
        self.pid, self.project = self.ensure_project_exists()

    def test_empty(self):
        from pillar.api.eve_settings import nodes_schema
        self.assertInvalid({}, nodes_schema)

    def test_asset(self):
        from pillar.api.eve_settings import nodes_schema

        file_id, _ = self.ensure_file_exists()

        node = {
            'name': '"The Harmless Prototype™"',
            'project': self.pid,
            'node_type': 'asset',
            'properties': {
                'status': 'published',
                'content_type': 'image',
                'file': file_id,
            },
            'user': self.user_id,
            'short_code': 'ABC333',
        }
        self.assertValid(node, nodes_schema)

    def test_asset_invalid_properties(self):
        from pillar.api.eve_settings import nodes_schema

        file_id, _ = self.ensure_file_exists()

        node = {
            'name': '"The Harmless Prototype™"',
            'project': self.pid,
            'node_type': 'asset',
            'properties': {
                'status': 'invalid-status',
                'content_type': 'image',
                'file': file_id,
            },
            'user': self.user_id,
            'short_code': 'ABC333',
        }
        self.assertInvalid(node, nodes_schema)

    def test_comment(self):
        from pillar.api.eve_settings import nodes_schema

        file_id, _ = self.ensure_file_exists()

        node = {
            'name': '"The Harmless Prototype™"',
            'project': self.pid,
            'node_type': 'asset',
            'properties': {
                'status': 'published',
                'content_type': 'image',
                'file': file_id,
            },
            'user': self.user_id,
            'short_code': 'ABC333',
        }
        node_id = self.create_node(node)

        comment = {
            'name': 'comment on some node',
            'project': self.pid,
            'node_type': 'comment',
            'properties': {
                'content': 'this is a comment',
                'status': 'published',
            },
            'parent': node_id,
        }
        self.assertValid(comment, nodes_schema)
