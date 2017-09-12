import collections
import datetime

from bson import ObjectId, tz_util
from pymongo.results import UpdateResult

from pillar.tests import AbstractPillarTest


class OrphanFilesTest(AbstractPillarTest):
    def test_find_orphan_files(self):
        self.enter_app_context()

        public1, _ = self.create_project_with_admin(
            24 * 'a', project_overrides={'_id': ObjectId(), 'is_private': False})
        public2, _ = self.create_project_with_admin(
            24 * 'b', project_overrides={'_id': ObjectId(), 'is_private': False})
        private1, _ = self.create_project_with_admin(
            24 * 'c', project_overrides={'_id': ObjectId(), 'is_private': True})
        private2, _ = self.create_project_with_admin(
            24 * 'd', project_overrides={'_id': ObjectId(), 'is_private': None})
        self.assertEqual(4, self.app.db('projects').count())

        # Create files, some orphan and some used.
        project_ids = (public1, public2, private1, private2)
        file_ids = collections.defaultdict(list)
        for pidx, pid in enumerate(project_ids):
            for filenum in range(5):
                generated_file_id = ObjectId(f'{pidx}{filenum}' + 22 * 'a')
                file_id, _ = self.ensure_file_exists({
                    '_id': generated_file_id,
                    'project': pid,
                    'name': f'Test file p{pid} num {filenum}'
                })
                file_ids[pid].append(file_id)

        proj_coll = self.app.db('projects')
        for pid in project_ids:
            fids = file_ids[pid]

            # Use fids[4] as project image
            res: UpdateResult = proj_coll.update_one({'_id': pid},
                                 {'$set': {'picture': fids[4]}})
            self.assertEqual(1, res.matched_count)
            self.assertEqual(1, res.modified_count)

            # Asset linking directly to fids[0]
            self.create_node({
                '_id': ObjectId(),
                'project': pid,
                'picture': ObjectId('572761f39837730efe8e1210'),
                'description': '',
                'node_type': 'asset',
                'user': ObjectId(24 * 'a'),
                'properties': {
                    'status': 'published',
                    'content_type': 'image',
                    'file': fids[0],
                },
                'name': 'Image direct link',
                '_updated': datetime.datetime(2016, 5, 2, 14, 19, 58, 0, tzinfo=tz_util.utc),
                '_created': datetime.datetime(2016, 5, 2, 14, 19, 37, 0, tzinfo=tz_util.utc),
                '_etag': '6b8589b42c880e3626f43f3e82a5c5b946742687'
            })
            # Some other node type that has some random field pointing to fids[1].
            self.create_node({
                '_id': ObjectId(),
                'project': pid,
                'picture': ObjectId('572761f39837730efe8e1210'),
                'description': '',
                'node_type': 'totally-unknown',
                'user': ObjectId(24 * 'a'),
                'properties': {
                    'status': 'published',
                    'content_type': 'image',
                    'file': fids[0],
                    'random': {'field': [fids[1]]}
                },
                'name': 'Image random field',
                '_updated': datetime.datetime(2016, 5, 2, 14, 19, 58, 0, tzinfo=tz_util.utc),
                '_created': datetime.datetime(2016, 5, 2, 14, 19, 37, 0, tzinfo=tz_util.utc),
                '_etag': '6b8589b42c880e3626f43f3e82a5c5b946742687'
            })
            # Completely unknown collection with document that points to fids[2]
            unknown_coll = self.app.db('unknown')
            unknown_coll.insert_one({
                'project': pid,
                'random': {'field': [fids[2]]}
            })
            # fids[3] is an orphan.

        from pillar.cli.maintenance import _find_orphan_files

        for pid in project_ids:
            orphans = _find_orphan_files(pid)
            self.assertEqual({file_ids[pid][3]}, orphans)
