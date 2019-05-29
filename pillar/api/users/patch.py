"""User patching support."""

import logging

import bson
from flask import Blueprint
import werkzeug.exceptions as wz_exceptions

from pillar import current_app
from pillar.auth import current_user
from pillar.api.utils import authorization, jsonify, remove_private_keys
from pillar.api import patch_handler

log = logging.getLogger(__name__)
patch_api_blueprint = Blueprint('users.patch', __name__)


class UserPatchHandler(patch_handler.AbstractPatchHandler):
    item_name = 'user'

    @authorization.require_login()
    def patch_set_username(self, user_id: bson.ObjectId, patch: dict):
        """Updates a user's username."""
        if user_id != current_user.user_id:
            log.info('User %s tried to change username of user %s',
                     current_user.user_id, user_id)
            raise wz_exceptions.Forbidden('You may only change your own username')

        new_username = patch['username']
        log.info('User %s uses PATCH to set username to %r', current_user.user_id, new_username)

        users_coll = current_app.db('users')
        db_user = users_coll.find_one({'_id': user_id})
        db_user['username'] = new_username

        # Save via Eve to check the schema and trigger update hooks.
        response, _, _, status = current_app.put_internal(
            'users', remove_private_keys(db_user), _id=user_id)

        return jsonify(response), status


def setup_app(app, url_prefix):
    UserPatchHandler(patch_api_blueprint)
    app.register_api_blueprint(patch_api_blueprint, url_prefix=url_prefix)
