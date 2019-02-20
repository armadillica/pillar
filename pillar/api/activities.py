import logging

from flask import request, current_app
from pillar.api.utils import gravatar
from pillar.auth import current_user

log = logging.getLogger(__name__)


def notification_parse(notification):
    activities_collection = current_app.data.driver.db['activities']
    activities_subscriptions_collection = \
        current_app.data.driver.db['activities-subscriptions']
    users_collection = current_app.data.driver.db['users']
    nodes_collection = current_app.data.driver.db['nodes']
    activity = activities_collection.find_one({'_id': notification['activity']})

    if activity is None or activity['object_type'] != 'node':
        return
    node = nodes_collection.find_one({'_id': activity['object']})
    if not node:
        # This can happen when a notification is generated and then the
        # node is deleted.
        return

    # Initial support only for node_type comments
    if node['node_type'] != 'comment':
        return
    node['parent'] = nodes_collection.find_one({'_id': node['parent']})
    object_type = 'comment'
    object_name = ''
    object_id = activity['object']

    if node['parent']['user'] == current_user.user_id:
        owner = "your {0}".format(node['parent']['node_type'])
    else:
        parent_comment_user = users_collection.find_one(
            {'_id': node['parent']['user']})
        if parent_comment_user['_id'] == node['user']:
            user_name = 'their'
        else:
            user_name = "{0}'s".format(parent_comment_user['username'])
        owner = "{0} {1}".format(user_name, node['parent']['node_type'])

    context_object_type = node['parent']['node_type']
    context_object_name = owner
    context_object_id = activity['context_object']
    if activity['verb'] == 'replied':
        action = 'replied to'
    elif activity['verb'] == 'commented':
        action = 'left a comment on'
    else:
        action = activity['verb']

    lookup = {
        'user': current_user.user_id,
        'context_object_type': 'node',
        'context_object': context_object_id,
    }
    subscription = activities_subscriptions_collection.find_one(lookup)
    if subscription and subscription['notifications']['web'] == True:
        is_subscribed = True
    else:
        is_subscribed = False

    # Parse user_actor
    actor = users_collection.find_one({'_id': activity['actor_user']})
    if actor:
        parsed_actor = {
            'username': actor['username'],
            'avatar': gravatar(actor['email'])}
    else:
        parsed_actor = None

    updates = dict(
        _id=notification['_id'],
        actor=parsed_actor,
        action=action,
        object_type=object_type,
        object_name=object_name,
        object_id=str(object_id),
        context_object_type=context_object_type,
        context_object_name=context_object_name,
        context_object_id=str(context_object_id),
        date=activity['_created'],
        is_read=('is_read' in notification and notification['is_read']),
        is_subscribed=is_subscribed,
        subscription=subscription['_id']
    )
    notification.update(updates)


def notification_get_subscriptions(context_object_type, context_object_id, actor_user_id):
    subscriptions_collection = current_app.data.driver.db['activities-subscriptions']
    lookup = {
        'user': {"$ne": actor_user_id},
        'context_object_type': context_object_type,
        'context_object': context_object_id,
        'is_subscribed': True,
    }
    return subscriptions_collection.find(lookup)


def activity_subscribe(user_id, context_object_type, context_object_id):
    """Subscribe a user to changes for a specific context. We create a subscription
    if none is found.

    :param user_id: id of the user we are going to subscribe
    :param context_object_type: hardcoded index, check the notifications/model.py
    :param context_object_id: object id, to be traced with context_object_type_id
    """
    subscriptions_collection = current_app.data.driver.db['activities-subscriptions']
    lookup = {
        'user': user_id,
        'context_object_type': context_object_type,
        'context_object': context_object_id
    }
    subscription = subscriptions_collection.find_one(lookup)

    # If no subscription exists, we create one
    if not subscription:
        # Workaround for issue: https://github.com/pyeve/eve/issues/1174
        lookup['notifications'] = {}
        current_app.post_internal('activities-subscriptions', lookup)


def activity_object_add(actor_user_id, verb, object_type, object_id,
                        context_object_type, context_object_id):
    """Add a notification object and creates a notification for each user that
    - is not the original author of the post
    - is actively subscribed to the object

    This works using the following pattern:

    ACTOR -> VERB -> OBJECT -> CONTEXT

    :param actor_user_id: id of the user who is changing the object
    :param verb: the action on the object ('commented', 'replied')
    :param object_type: hardcoded name
    :param object_id: object id, to be traced with object_type_id
    """

    subscriptions = notification_get_subscriptions(
        context_object_type, context_object_id, actor_user_id)

    if subscriptions.count() == 0:
        return

    info, status = register_activity(actor_user_id, verb, object_type, object_id,
                                     context_object_type, context_object_id)
    if status != 201:
        # If creation failed for any reason, do not create a any notifcation
        return

    for subscription in subscriptions:
        notification = dict(
            user=subscription['user'],
            activity=info['_id'])
        current_app.post_internal('notifications', notification)


def register_activity(actor_user_id, verb, object_type, object_id,
                      context_object_type, context_object_id,
                      project_id=None,
                      node_type=None):
    """Registers an activity.

    This works using the following pattern:

    ACTOR -> VERB -> OBJECT -> CONTEXT

    :param actor_user_id: id of the user who is changing the object
    :param verb: the action on the object ('commented', 'replied')
    :param object_type: hardcoded name, see database schema
    :param object_id: object id, to be traced with object_type
    :param context_object_type: the type of the context object, like 'project' or 'node',
        see database schema
    :param context_object_id:
    :param project_id: optional project ID to make the activity easily queryable
        per project.
    :param node_type: optional, node type of the node receiving the activity.

    :returns: tuple (info, status_code), where a successful operation should have
        status_code=201. If it is not 201, a warning is logged.
    """

    activity = {
        'actor_user': actor_user_id,
        'verb': verb,
        'object_type': object_type,
        'object': object_id,
        'context_object_type': context_object_type,
        'context_object': context_object_id}
    if project_id:
        activity['project'] = project_id
    if node_type:
        activity['node_type'] = node_type

    info, _, _, status_code = current_app.post_internal('activities', activity)

    if status_code != 201:
        log.error('register_activity: code %i creating activity %s: %s',
                  status_code, activity, info)
    else:
        log.info('register_activity: user %s "%s" on %s %s, context %s %s',
                 actor_user_id, verb, object_type, object_id,
                 context_object_type, context_object_id)
    return info, status_code


def before_returning_item_notifications(response):
    if request.args.get('parse'):
        notification_parse(response)


def before_returning_resource_notifications(response):
    for item in response['_items']:
        if request.args.get('parse'):
            notification_parse(item)


def setup_app(app):
    app.on_fetched_item_notifications += before_returning_item_notifications
    app.on_fetched_resource_notifications += before_returning_resource_notifications
