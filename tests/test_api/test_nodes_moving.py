import unittest
from unittest import mock

from bson import ObjectId
import pymongo.database

# Required to mock this module, otherwise 'pillar.api.file_storage' doesn't have
# the attribute 'moving'
import pillar.api.file_storage.moving


class NodeMoverTest(unittest.TestCase):
    def setUp(self):
        from pillar.api.nodes import moving

        self.db = mock.MagicMock(spec=pymongo.database.Database)
        self.mover = moving.NodeMover(db=self.db)

    def test_file_generator(self):
        # Degenerate cases.
        self.assertEqual([], list(self.mover._files(None)))
        self.assertEqual([], list(self.mover._files([])))
        self.assertEqual([], list(self.mover._files({})))

        # Single ID
        self.assertEqual([ObjectId(24 * 'a')],
                         list(self.mover._files(ObjectId(24 * 'a'))))

        # Keyed single ID
        self.assertEqual([ObjectId(24 * 'a')],
                         list(self.mover._files({'file': ObjectId(24 * 'a')}, 'file')))

        # Keyed list of IDs
        self.assertEqual([ObjectId(24 * 'a'), ObjectId(24 * 'b')],
                         list(self.mover._files({'files': [ObjectId(24 * 'a'), ObjectId(24 * 'b')]},
                                                'files')))

        # Keyed dict with keyed list of IDs
        self.assertEqual([ObjectId(24 * 'a'), ObjectId(24 * 'b')],
                         list(self.mover._files(
                             {'attachments': {'files': [ObjectId(24 * 'a'), ObjectId(24 * 'b')]}},
                             'attachments', 'files')))

        # Keyed dict with list of keyed lists of IDs
        found = self.mover._files(
            {'attachments': [
                {'files': [ObjectId(24 * 'a'), ObjectId(24 * 'b')]},
                {'files': [ObjectId(24 * 'c'), ObjectId(24 * 'd')]}]},
            'attachments', 'files')
        self.assertEqual(
            [ObjectId(24 * 'a'), ObjectId(24 * 'b'), ObjectId(24 * 'c'), ObjectId(24 * 'd')],
            list(found))

        # And one step futher
        found = self.mover._files(
            {'attachments': [
                {'files': [{'file': ObjectId(24 * 'a')},
                           {'file': ObjectId(24 * 'b')}]},
                {'files': [{'file': ObjectId(24 * 'c')},
                           {'file': ObjectId(24 * 'd')}]}
            ]},
            'attachments', 'files', 'file')
        self.assertEqual(
            [ObjectId(24 * 'a'), ObjectId(24 * 'b'), ObjectId(24 * 'c'), ObjectId(24 * 'd')],
            list(found))

        # Test double IDs
        found = self.mover._files(
            {'attachments': [
                {'files': [{'file': ObjectId(24 * 'a')},
                           {'file': ObjectId(24 * 'b')}]},
                {'files': [{'file': ObjectId(24 * 'a')},
                           {'file': ObjectId(24 * 'd')}]}
            ]},
            'attachments', 'files', 'file')
        self.assertEqual(
            [ObjectId(24 * 'a'), ObjectId(24 * 'b'), ObjectId(24 * 'a'), ObjectId(24 * 'd')],
            list(found))

    @mock.patch('pillar.api.file_storage.moving', autospec=True)
    def test_move_nodes(self, mock_fsmoving):
        node = {
            '_id': ObjectId(24 * 'a'),
            'picture': ObjectId(24 * 'b'),
            'properties': {
                'attachments': [
                    {'files': [
                        {'file': ObjectId(24 * 'c')},
                        {'file': ObjectId(24 * 'd')},
                    ]}
                ],
                'files': [
                    {'file': ObjectId(24 * 'e')},
                    {'file': ObjectId(24 * 'b')},
                ],
            }
        }
        prid = ObjectId(b'project_dest')
        new_project = {
            '_id': prid
        }

        update_res = mock.Mock()
        update_res.matched_count = 1
        update_res.modified_count = 1
        self.db['nodes'].update_one.return_value = update_res
        self.mover.change_project(node, new_project)

        mock_fsmoving.move_to_bucket.assert_has_calls([
            mock.call(ObjectId(24 * 'b'), prid, skip_storage=False),
            mock.call(ObjectId(24 * 'e'), prid, skip_storage=False),
            mock.call(ObjectId(24 * 'c'), prid, skip_storage=False),
            mock.call(ObjectId(24 * 'd'), prid, skip_storage=False),
        ])

    @mock.patch('pillar.api.file_storage.moving', autospec=True)
    def test_move_node_without_picture_or_att(self, mock_fsmoving):
        node = {
            '_id': ObjectId(24 * 'a'),
            'properties': {
                'files': [
                    {'file': ObjectId(24 * 'e')},
                    {'file': ObjectId(24 * 'b')},
                ],
            }
        }
        prid = ObjectId(b'project_dest')
        new_project = {
            '_id': prid
        }

        update_res = mock.Mock()
        update_res.matched_count = 1
        update_res.modified_count = 1
        self.db['nodes'].update_one.return_value = update_res
        self.mover.change_project(node, new_project)

        mock_fsmoving.move_to_bucket.assert_has_calls([
            mock.call(ObjectId(24 * 'e'), prid, skip_storage=False),
            mock.call(ObjectId(24 * 'b'), prid, skip_storage=False),
        ])
