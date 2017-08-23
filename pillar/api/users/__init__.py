import logging

import bson
from flask import current_app

from . import hooks
from .routes import blueprint_api

log = logging.getLogger(__name__)


def remove_user_from_group(user_id: bson.ObjectId, group_id: bson.ObjectId):
    """Removes the user from the given group.

    Directly uses MongoDB, so that it doesn't require any special permissions.
    """

    log.info('Removing user %s from group %s', user_id, group_id)
    user_group_action(user_id, group_id, '$pull')


def add_user_to_group(user_id: bson.ObjectId, group_id: bson.ObjectId):
    """Makes the user member of the given group.

    Directly uses MongoDB, so that it doesn't require any special permissions.
    """

    log.info('Adding user %s to group %s', user_id, group_id)
    user_group_action(user_id, group_id, '$addToSet')


def user_group_action(user_id: bson.ObjectId, group_id: bson.ObjectId, action: str):
    """Performs a group action (add/remove).
    
    :param user_id: the user's ObjectID.
    :param group_id: the group's ObjectID.
    :param action: either '$pull' to remove from a group, or '$addToSet' to add to a group.
    """

    from pymongo.results import UpdateResult

    assert isinstance(user_id, bson.ObjectId)
    assert isinstance(group_id, bson.ObjectId)
    assert action in {'$pull', '$addToSet'}

    users_coll = current_app.db('users')
    result: UpdateResult = users_coll.update_one(
        {'_id': user_id},
        {action: {'groups': group_id}},
    )

    if result.matched_count == 0:
        raise ValueError(f'Unable to {action} user {user_id} membership of group {group_id}; '
                         f'user not found.')


def _update_algolia_user_changed_role(sender, user: dict):
    log.debug('Sending updated user %s to Algolia due to role change', user['_id'])
    hooks.push_updated_user_to_algolia(user, original=None)


def setup_app(app, api_prefix):
    from pillar.api import service

    app.on_pre_GET_users += hooks.check_user_access
    app.on_post_GET_users += hooks.post_GET_user
    app.on_pre_PUT_users += hooks.check_put_access
    app.on_pre_PUT_users += hooks.before_replacing_user
    app.on_replaced_users += hooks.push_updated_user_to_algolia
    app.on_replaced_users += hooks.send_blinker_signal_roles_changed
    app.on_fetched_item_users += hooks.after_fetching_user
    app.on_fetched_resource_users += hooks.after_fetching_user_resource

    app.on_insert_users += hooks.before_inserting_users
    app.on_inserted_users += hooks.after_inserting_users

    app.register_api_blueprint(blueprint_api, url_prefix=api_prefix)

    service.signal_user_changed_role.connect(_update_algolia_user_changed_role)
