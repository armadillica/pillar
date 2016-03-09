from flask import g
from eve.methods.post import post_internal
from application import app

def notification_parse(notification):
    # notification = dict(a='n')
    # TODO: finish fixing this
    activities_collection = app.data.driver.db['activities']
    activities_subscriptions_collection = app.data.driver.db['activities-subscriptions']
    users_collection = app.data.driver.db['users']
    nodes_collection = app.data.driver.db['nodes']
    activity = activities_collection.find_one({'_id': notification['activity']})
    # actor = users_collection.find_one({'_id': activity['actor_user']})
    # Context is optional
    context_object_type = None
    context_object_name = None
    context_object_url = None

    if activity['object_type'] != 'node':
        return
    node = nodes_collection.find_one({'_id': activity['object']})
    # Initial support only for node_type comments
    if node['node_type'] != 'comment':
        return
    node['parent'] = nodes_collection.find_one({'_id': node['parent']})
    object_type = 'comment'
    object_name = ''
    object_id = activity['object']

    if node['parent']['user'] == g.current_user['user_id']:
        owner = "your {0}".format(node['parent']['node_type'])
    else:

        parent_comment_user = users_collection.find_one(
            {'_id': node['parent']['user']})
        owner = "{0}'s {1}".format(parent_comment_user['username'],
            node['parent']['node_type'])

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
        'user': g.current_user['user_id'],
        'context_object_type': 'node',
        'context_object': context_object_id,
    }

    subscription = activities_subscriptions_collection.find_one(lookup)
    if subscription and subscription['notifications']['web'] == True:
        is_subscribed = True
    else:
        is_subscribed = False

    updates = dict(
        _id=notification['_id'],
        actor=activity['actor_user'],
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
    subscriptions_collection = app.data.driver.db['activities-subscriptions']
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
    subscriptions_collection = app.data.driver.db['activities-subscriptions']
    lookup = {
        'user': user_id,
        'context_object_type': context_object_type,
        'context_object': context_object_id
    }
    subscription = subscriptions_collection.find_one(lookup)

    # If no subscription exists, we create one
    if not subscription:
        post_internal('activities-subscriptions', lookup)


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

    if subscriptions.count():
        activity = dict(
            actor_user=actor_user_id,
            verb=verb,
            object_type=object_type,
            object=object_id,
            context_object_type=context_object_type,
            context_object=context_object_id
            )

        activity = post_internal('activities', activity)
        if activity[3] != 201:
            # If creation failed for any reason, do not create a any notifcation
            return
        for subscription in subscriptions:
            notification = dict(
                user=subscription['user'],
                activity=activity[0]['_id'])
            post_internal('notifications', notification)
