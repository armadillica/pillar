# -*- encoding: utf-8 -*-

import unittest

from bson import ObjectId
from pillar.tests import AbstractPillarTest
from werkzeug.exceptions import BadRequest


class Str2idTest(AbstractPillarTest):
    def test_happy(self):
        from pillar.api.utils import str2id

        def happy(str_id):
            self.assertEqual(ObjectId(str_id), str2id(str_id))

        happy(24 * 'a')
        happy(12 * 'a')
        happy('577e23ad98377323f74c368c')

    def test_unhappy(self):
        from pillar.api.utils import str2id

        def unhappy(str_id):
            self.assertRaises(BadRequest, str2id, str_id)

        unhappy(13 * 'a')
        unhappy('577e23ad 8377323f74c368c')
        unhappy('김치')  # Kimchi
        unhappy('')
        unhappy('')
        unhappy(None)


class DocDiffTest(unittest.TestCase):
    def test_no_diff_simple(self):
        from pillar.api.utils import doc_diff
        diff = doc_diff({'a': 'b', 3: 42},
                        {'a': 'b', 3: 42})

        self.assertEqual([], list(diff))

    def test_no_diff_privates(self):
        from pillar.api.utils import doc_diff
        diff = doc_diff({'a': 'b', 3: 42, '_updated': 5133},
                        {'a': 'b', 3: 42, '_updated': 42})

        self.assertEqual([], list(diff))

    def test_diff_values_simple(self):
        from pillar.api.utils import doc_diff
        diff = doc_diff({'a': 'b', 3: 42},
                        {'a': 'b', 3: 513})

        self.assertEqual([(3, 42, 513)], list(diff))

    def test_diff_values_falsey(self):
        from pillar.api.utils import doc_diff, DoesNotExist

        # DoesNotExist vs. empty string
        diff = doc_diff({'a': 'b', 3: ''},
                        {'a': 'b'})
        self.assertEqual([], list(diff))

        diff = doc_diff({'a': 'b', 3: ''},
                        {'a': 'b'}, falsey_is_equal=False)
        self.assertEqual([(3, '', DoesNotExist)], list(diff))

        # Empty string vs. None
        diff = doc_diff({'a': 'b', 3: ''},
                        {'a': 'b', 3: None})
        self.assertEqual([], list(diff))

        diff = doc_diff({'a': 'b', 3: ''},
                        {'a': 'b', 3: None}, falsey_is_equal=False)
        self.assertEqual([(3, '', None)], list(diff))

    def test_diff_keys_simple(self):
        from pillar.api.utils import doc_diff, DoesNotExist
        diff = doc_diff({'a': 'b', 3: 42},
                        {'a': 'b', 2: 42})

        self.assertEqual({(3, 42, DoesNotExist), (2, DoesNotExist, 42)}, set(diff))

    def test_no_diff_nested(self):
        from pillar.api.utils import doc_diff
        diff = doc_diff({'a': 'b', 'props': {'status': 'todo', 'notes': 'jemoeder'}},
                        {'a': 'b', 'props': {'status': 'todo', 'notes': 'jemoeder'}})

        self.assertEqual([], list(diff))

    def test_diff_values_nested(self):
        from pillar.api.utils import doc_diff
        diff = doc_diff({'a': 'b', 'props': {'status': 'todo', 'notes': 'jemoeder'}},
                        {'a': 'c', 'props': {'status': 'done', 'notes': 'jemoeder'}})

        self.assertEqual({('a', 'b', 'c'), ('props.status', 'todo', 'done')},
                         set(diff))

    def test_diff_keys_nested(self):
        from pillar.api.utils import doc_diff, DoesNotExist
        diff = doc_diff({'a': 'b', 'props': {'status1': 'todo', 'notes': 'jemoeder'}},
                        {'a': 'b', 'props': {'status2': 'todo', 'notes': 'jemoeder'}})

        self.assertEqual({('props.status1', 'todo', DoesNotExist),
                          ('props.status2', DoesNotExist, 'todo')},
                         set(diff))


class NodeSetattrTest(unittest.TestCase):
    def test_simple(self):
        from pillar.api.utils import node_setattr

        node = {}
        node_setattr(node, 'a', 5)
        self.assertEqual({'a': 5}, node)

        node_setattr(node, 'b', {'complexer': 'value'})
        self.assertEqual({'a': 5, 'b': {'complexer': 'value'}}, node)

    def test_dotted(self):
        from pillar.api.utils import node_setattr

        node = {}
        self.assertRaises(KeyError, node_setattr, node, 'a.b', 5)

        node = {'b': {}}
        node_setattr(node, 'b.simple', 'value')
        self.assertEqual({'b': {'simple': 'value'}}, node)

        node_setattr(node, 'b.complex', {'yes': 'value'})
        self.assertEqual({'b': {'simple': 'value',
                                'complex': {'yes': 'value'}}}, node)

        node_setattr(node, 'b.complex', {'yes': 5})
        self.assertEqual({'b': {'simple': 'value',
                                'complex': {'yes': 5}}}, node)

    def test_none_simple(self):
        from pillar.api.utils import node_setattr

        node = {}
        node_setattr(node, 'a', None)
        node_setattr(node, None, 'b')
        self.assertEqual({None: 'b'}, node)

    def test_none_dotted(self):
        from pillar.api.utils import node_setattr

        node = {}
        self.assertRaises(KeyError, node_setattr, node, 'a.b', None)

        node = {'b': {}}
        node_setattr(node, 'b.simple', None)
        self.assertEqual({'b': {}}, node)

        node_setattr(node, 'b.complex', {'yes': None})
        self.assertEqual({'b': {'complex': {'yes': None}}}, node)

        node_setattr(node, 'b.complex.yes', None)
        self.assertEqual({'b': {'complex': {}}}, node)

        node_setattr(node, 'b.complex', {None: 5})
        self.assertEqual({'b': {'complex': {None: 5}}}, node)

