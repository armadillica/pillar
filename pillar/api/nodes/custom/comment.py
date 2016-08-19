"""PATCH support for comment nodes."""
import logging

import werkzeug.exceptions as wz_exceptions
from flask import current_app
from pillar.api.utils import authorization, authentication, jsonify

from . import register_patch_handler

log = logging.getLogger(__name__)
ROLES_FOR_COMMENT_VOTING = {u'subscriber', u'demo'}
VALID_COMMENT_OPERATIONS = {u'upvote', u'downvote', u'revoke'}


@register_patch_handler(u'comment')
def patch_comment(node_id, patch):
    assert_is_valid_patch(node_id, patch)
    user_id = authentication.current_user_id()

    # Find the node
    nodes_coll = current_app.data.driver.db['nodes']
    node_query = {'_id': node_id,
                  '$or': [{'properties.ratings.$.user': {'$exists': False}},
                          {'properties.ratings.$.user': user_id}]}
    node = nodes_coll.find_one(node_query,
                               projection={'properties': 1})
    if node is None:
        log.warning('How can the node not be found?')
        raise wz_exceptions.NotFound('Node %s not found' % node_id)

    props = node['properties']

    # Find the current rating (if any)
    rating = next((rating for rating in props.get('ratings', ())
                   if rating.get('user') == user_id), None)

    def revoke():
        if not rating:
            # No rating, this is a no-op.
            return

        label = 'positive' if rating.get('is_positive') else 'negative'
        update = {'$pull': {'properties.ratings': rating},
                  '$inc': {'properties.rating_%s' % label: -1}}
        return update

    def upvote():
        if rating and rating.get('is_positive'):
            # There already was a positive rating, so this is a no-op.
            return

        update = {'$inc': {'properties.rating_positive': 1}}
        if rating:
            update['$inc']['properties.rating_negative'] = -1
            update['$set'] = {'properties.ratings.$.is_positive': True}
        else:
            update['$push'] = {'properties.ratings': {
                'user': user_id, 'is_positive': True,
            }}
        return update

    def downvote():
        if rating and not rating.get('is_positive'):
            # There already was a negative rating, so this is a no-op.
            return

        update = {'$inc': {'properties.rating_negative': 1}}
        if rating:
            update['$inc']['properties.rating_positive'] = -1
            update['$set'] = {'properties.ratings.$.is_positive': False}
        else:
            update['$push'] = {'properties.ratings': {
                'user': user_id, 'is_positive': False,
            }}
        return update

    actions = {
        u'upvote': upvote,
        u'downvote': downvote,
        u'revoke': revoke,
    }
    action = actions[patch['op']]
    mongo_update = action()

    if mongo_update:
        log.info('Running %s', mongo_update)
        if rating:
            result = nodes_coll.update_one({'_id': node_id, 'properties.ratings.user': user_id},
                                           mongo_update)
        else:
            result = nodes_coll.update_one({'_id': node_id}, mongo_update)
    else:
        result = 'no-op'

    # Fetch the new ratings, so the client can show these without querying again.
    node = nodes_coll.find_one(node_id,
                               projection={'properties.rating_positive': 1,
                                           'properties.rating_negative': 1})

    return jsonify({'_status': 'OK',
                    'result': result,
                    'properties': node['properties']
                    })


def assert_is_valid_patch(node_id, patch):
    """Raises an exception when the patch isn't valid."""

    try:
        op = patch['op']
    except KeyError:
        raise wz_exceptions.BadRequest("PATCH should have a key 'op' indicating the operation.")

    if op not in VALID_COMMENT_OPERATIONS:
        raise wz_exceptions.BadRequest('Operation should be one of %s',
                                       ', '.join(VALID_COMMENT_OPERATIONS))

    # See whether the user is allowed to patch
    if authorization.user_matches_roles(ROLES_FOR_COMMENT_VOTING):
        log.debug('User is allowed to upvote/downvote comment')
        return

    # Access denied.
    log.info('User %s wants to PATCH comment node %s, but is not allowed.',
             authentication.current_user_id(), node_id)
    raise wz_exceptions.Forbidden()
