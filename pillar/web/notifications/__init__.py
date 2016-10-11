import logging
from flask import jsonify
from flask import Blueprint
from flask import request
from flask import url_for
from flask import abort
from flask_login import login_required, current_user
from pillarsdk.activities import Notification
from pillarsdk.activities import ActivitySubscription
from pillar.web.utils import system_util
from pillar.web.utils import pretty_date

log = logging.getLogger(__name__)
blueprint = Blueprint('notifications', __name__)


def notification_parse(notification):
    if notification.actor:
        username = notification.actor['username']
        avatar = notification.actor['avatar']
    else:
        return None
    return dict(
        _id=notification['_id'],
        username=username,
        username_avatar=avatar,
        action=notification.action,
        object_type=notification.object_type,
        object_name=notification.object_name,
        object_url=url_for(
            'nodes.redirect_to_context', node_id=notification.object_id),
        context_object_type=notification.context_object_type,
        context_object_name=notification.context_object_name,
        context_object_url=url_for(
            'nodes.redirect_to_context', node_id=notification.context_object_id),
        date=pretty_date(notification['_created'], detail=True),
        is_read=notification.is_read,
        is_subscribed=notification.is_subscribed,
        subscription=notification.subscription
        )


@blueprint.route('/')
@login_required
def index():
    """Get notifications for the current user.

    Optional url args:
    - limit: limits the number of notifications
    """
    limit = request.args.get('limit', 25)
    api = system_util.pillar_api()
    user_notifications = Notification.all({
        'where': {'user': str(current_user.objectid)},
        'sort': '-_created',
        'max_results': str(limit),
        'parse': '1'}, api=api)
    # TODO: properly investigate and handle missing actors
    items = [notification_parse(n) for n in user_notifications['_items'] if
             notification_parse(n)]

    return jsonify(items=items)


@blueprint.route('/<notification_id>/read-toggle')
@login_required
def action_read_toggle(notification_id):
    api = system_util.pillar_api()
    notification = Notification.find(notification_id, api=api)
    if notification.user == current_user.objectid:
        notification.is_read = not notification.is_read
        notification.update(api=api)
        return jsonify(
            status='success',
            data=dict(
                message="Notification {0} is_read {1}".format(
                    notification_id,
                    notification.is_read),
                is_read=notification.is_read))
    else:
        return abort(403)


@blueprint.route('/read-all')
@login_required
def action_read_all():
    """Mark all notifications as read"""
    api = system_util.pillar_api()
    notifications = Notification.all({
        'where': '{"user": "%s"}' % current_user.objectid,
        'sort': '-_created'}, api=api)

    for notification in notifications._items:
        notification = Notification.find(notification._id, api=api)
        notification.is_read = True
        notification.update(api=api)

    return jsonify(
        status='success',
        data=dict(message="All notifications mark as read"))


@blueprint.route('/<notification_id>/subscription-toggle')
@login_required
def action_subscription_toggle(notification_id):
    """Given a notification id, get the ActivitySubscription and update it by
    toggling the notifications status for the web key.
    """
    api = system_util.pillar_api()
    # Get the notification
    notification = notification_parse(
        Notification.find(notification_id, {'parse':'1'}, api=api))
    # Get the subscription and modify it
    subscription = ActivitySubscription.find(
        notification['subscription'], api=api)
    subscription.notifications['web'] = not subscription.notifications['web']
    subscription.update(api=api)
    return jsonify(
        status='success',
        data=dict(message="You have been {}subscribed".format(
            '' if subscription.notifications['web'] else 'un')))


def setup_app(app, url_prefix=None):
    app.register_blueprint(blueprint, url_prefix=url_prefix)
