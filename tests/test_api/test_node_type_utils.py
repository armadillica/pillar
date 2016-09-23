import unittest

from pillar.api.utils import node_type_utils


class NodeTypeUtilsTest(unittest.TestCase):
    def setUp(self):
        self.proj = {
            'permissions': {
                'users': [
                    {'user': 41,
                     'methods': ['GET', 'POST']},
                ],
                'groups': [
                    {'group': 1,
                     'methods': ['GET', 'PUT']},
                    {'group': 2,
                     'methods': ['DELETE']},
                ]
            }
        }
        self.node_type_1 = {'name': 'node-type-1'}
        self.node_type_2 = {'name': 'node-type-2'}
        self.node_types = [self.node_type_1, self.node_type_2]

    def test_trivial(self):
        def callback(*args):
            self.fail('Callback should not be called.')

        gen = node_type_utils.assign_permissions(self.proj, [], callback)
        self.assertEqual([], list(gen))

    def test_not_modified(self):
        def callback(*args):
            return []

        gen = node_type_utils.assign_permissions(self.proj, self.node_types, callback)
        new_types = list(gen)

        # They should be equal, but be copies, not references.
        self.assertEqual(self.node_types, new_types)
        self.assertIsNot(self.node_type_1, new_types[0])
        self.assertIsNot(self.node_type_2, new_types[1])

    def test_modified(self):
        def callback(node_type, ugw, ident, proj_methods):
            if node_type['name'] == 'node-type-1' and ugw == 'user':
                self.assertEqual(ident, 41)
                self.assertEqual(proj_methods, ['GET', 'POST'])
                return ['SPLOOSH']

            if node_type['name'] == 'node-type-2' and ugw == 'group':
                if ident == 1:
                    self.assertEqual(proj_methods, ['GET', 'PUT'])
                    return ['SPLASH', 'EEK']
                self.assertEqual(proj_methods, ['DELETE'])
                return ['OOF']

            if node_type['name'] == 'node-type-2' and ugw == 'world':
                self.assertEqual(proj_methods, [])
                return ['ICECREAM']

            return None

        gen = node_type_utils.assign_permissions(self.proj, self.node_types, callback)
        new_types = list(gen)

        # Only the additional permissions should be included in the node type.
        self.assertEqual({'name': 'node-type-1',
                          'permissions': {
                              'users': [
                                  {'user': 41,
                                   'methods': ['SPLOOSH']},
                              ],
                          }},
                         new_types[0])

        self.assertEqual({'name': 'node-type-2',
                          'permissions': {
                              'groups': [
                                  {'group': 1,
                                   'methods': ['SPLASH', 'EEK']},
                                  {'group': 2,
                                   'methods': ['OOF']},
                              ],
                              'world': ['ICECREAM']
                          }},
                         new_types[1])

    def test_already_existing(self):
        def callback(node_type, ugw, ident, proj_methods):
            if node_type['name'] == 'node-type-1' and ugw == 'user':
                return ['POST']

            if node_type['name'] == 'node-type-1' and ugw == 'world':
                self.assertIsNone(ident)
                return ['GET']

            return None

        self.node_type_1['permissions'] = {
            'users': [
                {'user': 41,
                 'methods': ['GET', 'POST']},
            ],
            'world': ['GET']
        }

        gen = node_type_utils.assign_permissions(self.proj, self.node_types, callback)
        new_types = list(gen)

        # These permissions are explicitly given to this node type, and even though are already
        # present on the project, should still be included here.
        self.assertEqual({'name': 'node-type-1',
                          'permissions': {
                              'users': [
                                  {'user': 41,
                                   'methods': ['POST']},
                              ],
                              'world': ['GET']
                          }},
                         new_types[0])

        self.assertEqual({'name': 'node-type-2'}, new_types[1])
