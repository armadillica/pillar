import logging

import bson
from flask import current_app

from . import hooks
from .routes import blueprint_api

log = logging.getLogger(__name__)


def add_user_to_group(user_id: bson.ObjectId, group_id: bson.ObjectId):
    """Makes the user member of the given group.
    
    Directly uses MongoDB, so that it doesn't require any special permissions.
    """

    from pymongo.results import UpdateResult

    assert isinstance(user_id, bson.ObjectId)
    assert isinstance(group_id, bson.ObjectId)

    log.info('Adding user %s to group %s', user_id, group_id)

    users_coll = current_app.db('users')
    db_user = users_coll.find_one(user_id, projection={'groups': 1})
    if db_user is None:
        raise ValueError('user %s not found', user_id, group_id)

    groups = set(db_user.get('groups', []))
    groups.add(group_id)

    # Sort the groups so that we have predictable, repeatable results.
    result: UpdateResult = users_coll.update_one(
        {'_id': db_user['_id']},
        {'$set': {'groups': sorted(groups)}})

    if result.matched_count == 0:
        raise ValueError('Unable to add user %s to group %s; user not found.')


def setup_app(app, api_prefix):
    app.on_pre_GET_users += hooks.check_user_access
    app.on_post_GET_users += hooks.post_GET_user
    app.on_pre_PUT_users += hooks.check_put_access
    app.on_pre_PUT_users += hooks.before_replacing_user
    app.on_replaced_users += hooks.push_updated_user_to_algolia
    app.on_replaced_users += hooks.send_blinker_signal_roles_changed
    app.on_fetched_item_users += hooks.after_fetching_user
    app.on_fetched_resource_users += hooks.after_fetching_user_resource

    app.register_api_blueprint(blueprint_api, url_prefix=api_prefix)
