from unittest import mock

from bson import ObjectId

from pillar.api.utils import random_etag, utcnow
from pillar.tests import AbstractPillarTest
from pillar.tests import common_test_data as ctd


class PurgeHomeProjectsTest(AbstractPillarTest):
    def test_purge(self):
        self.create_standard_groups()
        # user_a will be soft-deleted, user_b will be hard-deleted.
        # We don't support soft-deleting users yet, but the code should be
        # handling that properly anyway.
        user_a = self.create_user(user_id=24 * 'a', roles={'subscriber'}, token='token-a')
        user_b = self.create_user(user_id=24 * 'b', roles={'subscriber'}, token='token-b')

        # GET the home project to create it.
        home_a = self.get('/api/bcloud/home-project', auth_token='token-a').get_json()
        home_b = self.get('/api/bcloud/home-project', auth_token='token-b').get_json()

        with self.app.app_context():
            users_coll = self.app.db('users')

            res = users_coll.update_one({'_id': user_a}, {'$set': {'_deleted': True}})
            self.assertEqual(1, res.modified_count)

            res = users_coll.delete_one({'_id': user_b})
            self.assertEqual(1, res.deleted_count)

        from pillar.cli.maintenance import purge_home_projects

        with self.app.app_context():
            self.assertEqual(2, purge_home_projects(go=True))

            proj_coll = self.app.db('projects')
            self.assertEqual(True, proj_coll.find_one({'_id': ObjectId(home_a['_id'])})['_deleted'])
            self.assertEqual(True, proj_coll.find_one({'_id': ObjectId(home_b['_id'])})['_deleted'])


class UpgradeAttachmentSchemaTest(AbstractPillarTest):
    def test_blog_post(self):
        from pillar.api.node_types import PILLAR_NAMED_NODE_TYPES
        from pillar.cli.maintenance import upgrade_attachment_schema

        old_blog_post_nt = {
            "name": "post",
            "description": "A blog post, for any project",
            "dyn_schema": {
                "content": {
                    "type": "string",
                    "minlength": 5,
                    "maxlength": 90000,
                    "required": True
                },
                "status": {
                    "type": "string",
                    "allowed": ["published", "pending"],
                    "default": "pending"
                },
                "category": {"type": "string"},
                "url": {"type": "string"},
                "attachments": {
                    "type": "dict",
                    "keyschema": {"type": "string", "regex": "^[a-zA-Z0-9_ ]+$"},
                    "valueschema": {
                        "type": "dict",
                        "schema": {
                            "oid": {"type": "objectid", "required": True},
                            "link": {
                                "type": "string",
                                "allowed": ["self", "none", "custom"],
                                "default": "self"
                            },
                            "link_custom": {"type": "string"},
                            "collection": {
                                "type": "string",
                                "allowed": ["files"],
                                "default": "files"
                            }
                        }
                    }
                }
            },
            "form_schema": {},
            "parent": ["blog"]
        }

        pid, project = self.ensure_project_exists(
            project_overrides={
                'picture_header': None,
                'picture_square': None,
                'node_types': [
                    PILLAR_NAMED_NODE_TYPES['group_texture'],
                    PILLAR_NAMED_NODE_TYPES['group'],
                    PILLAR_NAMED_NODE_TYPES['asset'],
                    PILLAR_NAMED_NODE_TYPES['storage'],
                    PILLAR_NAMED_NODE_TYPES['comment'],
                    PILLAR_NAMED_NODE_TYPES['blog'],
                    old_blog_post_nt,
                ]})

        with self.app.app_context():
            upgrade_attachment_schema(proj_url=project['url'], go=True)

            db_proj = self.app.db('projects').find_one({'_id': pid})
            db_node_type = db_proj['node_types'][-1]
            self.assertEqual('post', db_node_type['name'])

            self.assertEqual(
                PILLAR_NAMED_NODE_TYPES['post']['dyn_schema'],
                db_node_type['dyn_schema'])
            self.assertEqual({}, db_node_type['form_schema'])


class ReconcileNodeDurationTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        super().setUp(**kwargs)
        self.pid, _ = self.ensure_project_exists()
        self.fake_now = utcnow()

        # Already correct. Should not be touched.
        self.node_id0 = self._create_video_node(file_duration=123, node_duration=123)
        # Out of sync, should be updated
        self.node_id1 = self._create_video_node(file_duration=3661, node_duration=15)
        self.node_id2 = self._create_video_node(file_duration=432, node_duration=5)
        self.node_id3 = self._create_video_node(file_duration=222)
        # No file duration. Should not be touched
        self.node_id4 = self._create_video_node()
        # No file. Should not be touched
        self.node_id5 = self._create_video_node(include_file=False)
        # Wrong node type. Should not be touched
        self.image_node_id = self._create_image_node()

        def id_to_original_dict(*nids):
            with self.app.app_context():
                nodes_coll = self.app.db('nodes')
                return dict(((nid, nodes_coll.find_one({'_id': nid})) for nid in nids))

        self.orig_nodes = id_to_original_dict(
            self.node_id0,
            self.node_id1,
            self.node_id2,
            self.node_id3,
            self.node_id4,
            self.node_id5,
            self.image_node_id,
        )

    def test_reconcile_all(self):
        from pillar.cli.maintenance import reconcile_node_video_duration

        with self.app.app_context():
            with mock.patch('pillar.api.utils.utcnow') as mock_utcnow:
                mock_utcnow.return_value = self.fake_now

                reconcile_node_video_duration(all_nodes=True, go=False)  # Dry run
                self.assertAllUnchanged()

                reconcile_node_video_duration(all_nodes=True, go=True)
                self.assertUnChanged(
                    self.node_id0,
                    self.node_id4,
                    self.image_node_id,
                )
                self.assertUpdated(self.node_id1, duration_seconds=3661)
                self.assertUpdated(self.node_id2, duration_seconds=432)
                self.assertUpdated(self.node_id3, duration_seconds=222)

    def test_reconcile_some(self):
        from pillar.cli.maintenance import reconcile_node_video_duration

        with self.app.app_context():
            with mock.patch('pillar.api.utils.utcnow') as mock_utcnow:
                mock_utcnow.return_value = self.fake_now

                to_reconcile = [str(self.node_id0), str(self.node_id1), str(self.node_id2),
                                str(self.node_id5)]
                reconcile_node_video_duration(nodes_to_update=to_reconcile, go=False)  # Dry run
                self.assertAllUnchanged()

                reconcile_node_video_duration(nodes_to_update=to_reconcile, go=True)
                self.assertUnChanged(
                    self.node_id0,
                    self.node_id3,
                    self.node_id4,
                    self.image_node_id,
                )
                self.assertUpdated(self.node_id1, duration_seconds=3661)
                self.assertUpdated(self.node_id2, duration_seconds=432)

    def assertUpdated(self, nid, duration_seconds):
        nodes_coll = self.app.db('nodes')
        new_node = nodes_coll.find_one({'_id': nid})
        orig_node = self.orig_nodes[nid]
        self.assertNotEqual(orig_node['_etag'], new_node['_etag'])
        self.assertEqual(self.fake_now, new_node['_updated'])
        self.assertEqual(duration_seconds, new_node['properties']['duration_seconds'])

    def assertAllUnchanged(self):
        self.assertUnChanged(*self.orig_nodes.keys())

    def assertUnChanged(self, *node_ids):
        nodes_coll = self.app.db('nodes')
        for nid in node_ids:
            new_node = nodes_coll.find_one({'_id': nid})
            orig_node = self.orig_nodes[nid]
            self.assertEqual(orig_node, new_node)

    def _create_video_node(self, file_duration=None, node_duration=None, include_file=True):
        file_id, _ = self.ensure_file_exists(file_overrides={
            '_id': ObjectId(),
            'content_type': 'video/mp4',
            'variations': [
                {'format': 'mp4',
                 'duration': file_duration
                 },
            ],
        })

        node = {
            'name': 'Just a node name',
            'project': self.pid,
            'description': '',
            'node_type': 'asset',
            '_etag': random_etag(),
        }
        props = {'status': 'published',
                 'content_type': 'video',
                 'order': 0}
        if node_duration is not None:
            props['duration_seconds'] = node_duration
        if include_file:
            props['file'] = file_id
        return self.create_node({
            'properties': props,
            **node})

    def _create_image_node(self):
        file_id, _ = self.ensure_file_exists(file_overrides={
            '_id': ObjectId(),
            'variations': [
                {'format': 'jpeg'},
            ],
        })

        node = {
            'name': 'Just a node name',
            'project': self.pid,
            'description': '',
            'node_type': 'asset',
            '_etag': random_etag(),
        }
        props = {'status': 'published',
                 'file': file_id,
                 'content_type': 'image',
                 'order': 0}
        return self.create_node({
            'properties': props,
            **node})


class DeleteProjectlessFilesTest(AbstractPillarTest):
    def test_delete_projectless_files(self):
        project1_id, _ = self.ensure_project_exists()
        project2_id, _ = self.ensure_project_exists(project_overrides={
            '_id': ObjectId(),
            '_deleted': True,
        })
        assert project1_id != project2_id

        # Project exists and is not soft-deleted:
        file1_id, file1_doc = self.ensure_file_exists()
        # Project exists but is soft-deleted:
        file2_id, file2_doc = self.ensure_file_exists(file_overrides={
            '_id': ObjectId(),
            'project': project2_id,
        })
        # Project does not exist:
        file3_id, file3_doc = self.ensure_file_exists(file_overrides={
            '_id': ObjectId(),
            'project': ObjectId(),
        })
        with self.app.app_context():
            self.app.db('projects').delete_one({'_id': file3_doc['project']})

        assert len({file1_id, file2_id, file3_id}) == 3

        from pillar.cli.maintenance import delete_projectless_files

        with self.app.app_context():
            delete_projectless_files(go=True)

            files_doc = self.app.db('files')
            found1 = files_doc.find_one(file1_id)
            found2 = files_doc.find_one(file2_id)
            found3 = files_doc.find_one(file3_id)
            self.assertNotIn('_deleted', found1, found1)
            self.assertIn('_deleted', found2, found2)
            self.assertIn('_deleted', found3, found3)
            self.assertTrue(found2['_deleted'], found2)
            self.assertTrue(found3['_deleted'], found3)

            self.assertLess(file2_doc['_updated'], found2['_updated'])
            self.assertLess(file3_doc['_updated'], found3['_updated'])

            self.assertNotEqual(file2_doc['_etag'], found2['_etag'])
            self.assertNotEqual(file3_doc['_etag'], found3['_etag'])

            # Delete the keys that should be changed so we can compare the rest.
            for key in {'_updated', '_etag', '_deleted'}:
                file2_doc.pop(key, ...)
                file3_doc.pop(key, ...)
                found2.pop(key, ...)
                found3.pop(key, ...)

            self.assertEqual(file1_doc, found1)
            self.assertEqual(file3_doc, found3)
            self.assertEqual(file3_doc, found3)


class FixMissingActivitiesSubscription(AbstractPillarTest):
    def test_fix_missing_activities_subscription(self):
        from pillar.cli.maintenance import fix_missing_activities_subscription_defaults

        with self.app.app_context():
            subscriptions_collection = self.app.db('activities-subscriptions')

            invalid_subscription = {
                'user': ObjectId(),
                'context_object_type': 'node',
                'context_object': ObjectId(),
            }

            valid_subscription = {
                'user': ObjectId(),
                'context_object_type': 'node',
                'context_object': ObjectId(),
                'is_subscribed': False,
                'notifications': {'web': False, }
            }

            result = subscriptions_collection.insert_one(
                invalid_subscription,
                bypass_document_validation=True)

            id_invalid = result.inserted_id

            result = subscriptions_collection.insert_one(
                valid_subscription,
                bypass_document_validation=True)

            id_valid = result.inserted_id

            fix_missing_activities_subscription_defaults()  # Dry run. Nothing should change
            invalid_subscription = subscriptions_collection.find_one({'_id': id_invalid})
            self.assertNotIn('is_subscribed', invalid_subscription.keys())
            self.assertNotIn('notifications', invalid_subscription.keys())

            fix_missing_activities_subscription_defaults(go=True)  # Real run. Invalid should be updated
            invalid_subscription = subscriptions_collection.find_one({'_id': id_invalid})
            self.assertTrue(invalid_subscription['is_subscribed'])
            self.assertTrue(invalid_subscription['notifications']['web'])

            # Was already ok. Should not have been updated
            valid_subscription = subscriptions_collection.find_one({'_id': id_valid})
            self.assertFalse(valid_subscription['is_subscribed'])
            self.assertFalse(valid_subscription['notifications']['web'])
