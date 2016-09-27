"""Code for moving around nodes."""

import attr
import flask_pymongo.wrappers
from bson import ObjectId

from pillar import attrs_extra
import pillar.api.file_storage.moving


@attr.s
class NodeMover(object):
    db = attr.ib(validator=attr.validators.instance_of(flask_pymongo.wrappers.Database))
    skip_gcs = attr.ib(default=False, validator=attr.validators.instance_of(bool))
    _log = attrs_extra.log('%s.NodeMover' % __name__)

    def change_project(self, node, dest_proj):
        """Moves a node and children to a new project."""

        assert isinstance(node, dict)
        assert isinstance(dest_proj, dict)

        for move_node in self._children(node):
            self._change_project(move_node, dest_proj)

    def _change_project(self, node, dest_proj):
        """Changes the project of a single node, non-recursively."""

        node_id = node['_id']
        proj_id = dest_proj['_id']
        self._log.info('Moving node %s to project %s', node_id, proj_id)

        # Find all files in the node.
        moved_files = set()
        self._move_files(moved_files, dest_proj, self._files(node.get('picture', None)))
        self._move_files(moved_files, dest_proj, self._files(node['properties'], 'file'))
        self._move_files(moved_files, dest_proj, self._files(node['properties'], 'files', 'file'))
        self._move_files(moved_files, dest_proj,
                         self._files(node['properties'], 'attachments', 'files', 'file'))

        # Switch the node's project after its files have been moved.
        self._log.info('Switching node %s to project %s', node_id, proj_id)
        nodes_coll = self.db['nodes']
        update_result = nodes_coll.update_one({'_id': node_id},
                                              {'$set': {'project': proj_id}})
        if update_result.matched_count != 1:
            raise RuntimeError(
                'Unable to update node %s in MongoDB: matched_count=%i; modified_count=%i' % (
                    node_id, update_result.matched_count, update_result.modified_count))

    def _move_files(self, moved_files, dest_proj, file_generator):
        """Tries to find all files from the given properties."""

        for file_id in file_generator:
            if file_id in moved_files:
                continue
            moved_files.add(file_id)
            self.move_file(dest_proj, file_id)

    def move_file(self, dest_proj, file_id):
        """Moves a single file to another project"""

        self._log.info('Moving file %s to project %s', file_id, dest_proj['_id'])
        pillar.api.file_storage.moving.gcs_move_to_bucket(file_id, dest_proj['_id'],
                                                          skip_gcs=self.skip_gcs)

    def _files(self, file_ref, *properties):
        """Yields file ObjectIDs."""

        # Degenerate cases.
        if not file_ref:
            return

        # Single ObjectID
        if isinstance(file_ref, ObjectId):
            assert not properties
            yield file_ref
            return

        # List of ObjectIDs
        if isinstance(file_ref, list):
            for item in file_ref:
                for subitem in self._files(item, *properties):
                    yield subitem
            return

        # Dict, use properties[0] as key
        if isinstance(file_ref, dict):
            try:
                subref = file_ref[properties[0]]
            except KeyError:
                # Silently skip non-existing keys.
                return

            for subitem in self._files(subref, *properties[1:]):
                yield subitem
            return

        raise TypeError('File ref is of type %s, not implemented' % type(file_ref))

    def _children(self, node):
        """Generator, recursively yields the node and its children."""

        yield node

        nodes_coll = self.db['nodes']
        for child in nodes_coll.find({'parent': node['_id']}):
            # "yield from self.children(child)" was introduced in Python 3.3
            for grandchild in self._children(child):
                yield grandchild
