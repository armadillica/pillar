import bson
import flask
from bson import ObjectId

from pillar.tests import AbstractPillarTest


class NotificationsTest(AbstractPillarTest):
    def setUp(self, **kwargs):
        super().setUp(**kwargs)
        self.project_id, _ = self.ensure_project_exists()
        self.user1_id = self.create_user(user_id=str(bson.ObjectId()))
        self.user2_id = self.create_user(user_id=str(bson.ObjectId()))

    def test_create_node(self):
        """When a node is created, a subscription should also be created"""

        with self.app.app_context():
            self.login_api_as(self.user1_id, roles={'subscriber', 'admin'},
                              # This group is hardcoded in the EXAMPLE_PROJECT.
                              group_ids=[ObjectId('5596e975ea893b269af85c0e')])

            node_id = self.post_node(self.user1_id)

            self.assertSubscribed(node_id, self.user1_id)
            self.assertNotSubscribed(node_id, self.user2_id)

    def test_comment_on_own_node(self):
        """A comment on my own node should not give me any notifications"""

        with self.app.app_context():
            self.login_api_as(self.user1_id, roles={'subscriber', 'admin'},
                              # This group is hardcoded in the EXAMPLE_PROJECT.
                              group_ids=[ObjectId('5596e975ea893b269af85c0e')])

            node_id = self.post_node(self.user1_id)
            comment_id = self.post_comment(node_id)

            self.assertSubscribed(comment_id, self.user1_id)
            self.assertNotSubscribed(comment_id, self.user2_id)

        with self.login_as(self.user1_id):
            notification = self.notification_for_object(comment_id)
            self.assertIsNone(notification)

    def test_comment_on_node(self):
        """A comment on some one else's node should give them a notification, and subscriptions should be created"""

        with self.app.app_context():
            self.login_api_as(self.user1_id, roles={'subscriber', 'admin'},
                              # This group is hardcoded in the EXAMPLE_PROJECT.
                              group_ids=[ObjectId('5596e975ea893b269af85c0e')])

            node_id = self.post_node(self.user1_id)

        with self.app.app_context():
            self.login_api_as(self.user2_id, roles={'subscriber', 'admin'},
                              # This group is hardcoded in the EXAMPLE_PROJECT.
                              group_ids=[ObjectId('5596e975ea893b269af85c0e')])
            comment_id = self.post_comment(node_id)

            self.assertSubscribed(comment_id, self.user2_id)
            self.assertNotSubscribed(comment_id, self.user1_id)
            self.assertSubscribed(node_id, self.user1_id, self.user2_id)

        with self.login_as(self.user1_id):
            notification = self.notification_for_object(comment_id)
            self.assertIsNotNone(notification)

    def test_mark_notification_as_read(self):
        with self.app.app_context():
            self.login_api_as(self.user1_id, roles={'subscriber', 'admin'},
                              # This group is hardcoded in the EXAMPLE_PROJECT.
                              group_ids=[ObjectId('5596e975ea893b269af85c0e')])

            node_id = self.post_node(self.user1_id)

        with self.app.app_context():
            self.login_api_as(self.user2_id, roles={'subscriber', 'admin'},
                              # This group is hardcoded in the EXAMPLE_PROJECT.
                              group_ids=[ObjectId('5596e975ea893b269af85c0e')])
            comment_id = self.post_comment(node_id)

        with self.login_as(self.user1_id):
            notification = self.notification_for_object(comment_id)
            self.assertFalse(notification['is_read'])

            is_read_toggle_url = flask.url_for('notifications.action_read_toggle', notification_id=notification['_id'])
            self.get(is_read_toggle_url)

            notification = self.notification_for_object(comment_id)
            self.assertTrue(notification['is_read'])

            self.get(is_read_toggle_url)

            notification = self.notification_for_object(comment_id)
            self.assertFalse(notification['is_read'])

    def test_unsubscribe(self):
        """It should be possible to unsubscribe to notifications"""
        with self.app.app_context():
            self.login_api_as(self.user1_id, roles={'subscriber', 'admin'},
                              # This group is hardcoded in the EXAMPLE_PROJECT.
                              group_ids=[ObjectId('5596e975ea893b269af85c0e')])

            node_id = self.post_node(self.user1_id)

        with self.app.app_context():
            self.login_api_as(self.user2_id, roles={'subscriber', 'admin'},
                              # This group is hardcoded in the EXAMPLE_PROJECT.
                              group_ids=[ObjectId('5596e975ea893b269af85c0e')])
            comment_id = self.post_comment(node_id)

        with self.login_as(self.user1_id):
            notification = self.notification_for_object(comment_id)
            self.assertTrue(notification['is_subscribed'])

            is_subscribed_toggle_url =\
                flask.url_for('notifications.action_subscription_toggle', notification_id=notification['_id'])
            self.get(is_subscribed_toggle_url)

            notification = self.notification_for_object(comment_id)
            self.assertFalse(notification['is_subscribed'])

        with self.app.app_context():
            self.login_api_as(self.user2_id, roles={'subscriber', 'admin'},
                              # This group is hardcoded in the EXAMPLE_PROJECT.
                              group_ids=[ObjectId('5596e975ea893b269af85c0e')])
            comment2_id = self.post_comment(node_id)

        with self.login_as(self.user1_id):
            notification = self.notification_for_object(comment2_id)
            self.assertFalse(notification['is_subscribed'])

    def assertSubscribed(self, node_id, *user_ids):
        subscriptions_col = self.app.data.driver.db['activities-subscriptions']

        lookup = {
            'context_object': node_id,
            'notifications.web': True,
        }
        subscriptions = list(subscriptions_col.find(lookup))
        self.assertEquals(len(subscriptions), len(user_ids))
        for s in subscriptions:
            self.assertIn(s['user'], user_ids)
            self.assertEquals(s['context_object_type'], 'node')

    def assertNotSubscribed(self, node_id, user_id):
        subscriptions_col = self.app.data.driver.db['activities-subscriptions']

        lookup = {
            'context_object': node_id,
        }
        subscriptions = subscriptions_col.find(lookup)
        for s in subscriptions:
            self.assertNotEquals(s['user'], user_id)

    def notification_for_object(self, node_id):
        notifications_url = flask.url_for('notifications.index')
        notification_items = self.get(notifications_url).json['items']

        object_url = flask.url_for('nodes.redirect_to_context', node_id=str(node_id), _external=False)
        for candidate in notification_items:
            if candidate['object_url'] == object_url:
                return candidate

    def post_node(self, user_id):
        node_doc = {'description': '',
                    'project': self.project_id,
                    'node_type': 'asset',
                    'user': user_id,
                    'properties': {'status': 'published',
                                   'tags': [],
                                   'order': 0,
                                   'categories': '',
                                   },
                    'name': 'My first test node'}

        r, _, _, status = self.app.post_internal('nodes', node_doc)
        self.assertEqual(status, 201, r)
        node_id = r['_id']
        return node_id

    def post_comment(self, node_id):
        comment_url = flask.url_for('nodes_api.post_node_comment', node_path=str(node_id))
        comment = self.post(
            comment_url,
            json={
                'msg': 'je möder lives at [home](https://cloud.blender.org/)',
            },
            expected_status=201,
        )
        return ObjectId(comment.json['id'])
