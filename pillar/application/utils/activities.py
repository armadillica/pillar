from eve.methods.post import post_internal
from application import app

# def notification_parse(notification):
#     # TODO: finish fixing this
#     activities_collection = app.data.driver.db['activities']
#     users_collection = app.data.driver.db['users']
#     nodes_collection = app.data.driver.db['nodes']
#     activity = activities_collection.find_one({'_id': notification['_id']})
#     actor = users_collection.find_one({'_id': activity['actor_user']})
#     # Context is optional
#     context_object_type = None
#     context_object_name = None
#     context_object_url = None

#     if activity['object_type'] == 'node':
#         node = nodes_collection.find_one({'_id': activity['object']})
#         # project = Project.find(node.project, {
#         #     'projection': '{"name":1, "url":1}'}, api=api)
#         # Initial support only for node_type comments
#         if node['node_type'] == 'comment':
#             # comment = Comment.query.get_or_404(notification_object.object_id)
#             node['parent'] = nodes_collection.find_one({'_id': node['parent']})
#             object_type = 'comment'
#             object_name = ''

#             object_url = url_for('nodes.view', node_id=node._id, redir=1)
#             if node.parent.user == current_user.objectid:
#                 owner = "your {0}".format(node.parent.node_type)
#             else:
#                 parent_comment_user = User.find(node.parent.user, api=api)
#                 owner = "{0}'s {1}".format(parent_comment_user.username,
#                     node.parent.node_type)

#             context_object_type = node.parent.node_type
#             context_object_name = owner
#             context_object_url = url_for('nodes.view', node_id=node.parent._id, redir=1)
#             if activity.verb == 'replied':
#                 action = 'replied to'
#             elif activity.verb == 'commented':
#                 action = 'left a comment on'
#             else:
#                 action = activity.verb
#         else:
#             return None
#     else:
#         return None

#     return dict(
#         _id=notification._id,
#         username=actor.username,
#         username_avatar=actor.gravatar(),
#         action=action,
#         object_type=object_type,
#         object_name=object_name,
#         object_url=object_url,
#         context_object_type=context_object_type,
#         context_object_name=context_object_name,
#         context_object_url=context_object_url,
#         date=pretty_date(activity._created),
#         is_read=notification.is_read,
#         # is_subscribed=notification.is_subscribed
#         )

def notification_get_subscriptions(context_object_type, context_object_id, actor_user_id):
    subscriptions_collection = app.data.driver.db['activities-subscriptions']
    lookup = {
        'user': {"$ne": actor_user_id},
        'context_object_type': context_object_type,
        'context_object': context_object_id,
        'is_subscribed': True,
    }
    return subscriptions_collection.find(lookup)


def activity_create(user_id, context_object_type, context_object_id):
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


def activity_subscribe(actor_user_id, verb, object_type, object_id,
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
        for subscription in subscriptions:
            notification = dict(
                user=subscription['user'],
                activity=activity[0]['_id'])
            post_internal('notifications', notification)
