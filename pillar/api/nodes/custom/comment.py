"""PATCH support for comment nodes."""

import logging

from eve.methods.patch import patch_internal
from flask import current_app
import werkzeug.exceptions as wz_exceptions

from pillar.api.utils import authorization, authentication, jsonify

from . import register_patch_handler

log = logging.getLogger(__name__)
ROLES_FOR_COMMENT_VOTING = {'subscriber', 'demo'}
COMMENT_VOTING_OPS = {'upvote', 'downvote', 'revoke'}
VALID_COMMENT_OPERATIONS = COMMENT_VOTING_OPS.union({'edit'})


@register_patch_handler('comment')
def patch_comment(node_id, patch):
    assert_is_valid_patch(node_id, patch)
    user_id = authentication.current_user_id()

    if patch['op'] in COMMENT_VOTING_OPS:
        result, node = vote_comment(user_id, node_id, patch)
    else:
        assert patch['op'] == 'edit', 'Invalid patch operation %s' % patch['op']
        result, node = edit_comment(user_id, node_id, patch)

    return jsonify({'_status': 'OK',
                    'result': result,
                    'properties': node['properties']
                    })


def vote_comment(user_id, node_id, patch):
    """Performs a voting operation."""

    # Find the node. Includes a query on the properties.ratings array so
    # that we only get the current user's rating.
    nodes_coll = current_app.data.driver.db['nodes']
    node_query = {'_id': node_id,
                  '$or': [{'properties.ratings.$.user': {'$exists': False}},
                          {'properties.ratings.$.user': user_id}]}
    node = nodes_coll.find_one(node_query,
                               projection={'properties': 1})
    if node is None:
        log.warning('User %s wanted to patch non-existing node %s' % (user_id, node_id))
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
        'upvote': upvote,
        'downvote': downvote,
        'revoke': revoke,
    }
    action = actions[patch['op']]
    mongo_update = action()

    nodes_coll = current_app.data.driver.db['nodes']
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

    return result, node


def edit_comment(user_id, node_id, patch):
    """Edits a single comment.

    Doesn't do permission checking; users are allowed to edit their own
    comment, and this is not something you want to revoke anyway. Admins
    can edit all comments.
    """

    # Find the node. We need to fetch some more info than we use here, so that
    # we can pass this stuff to Eve's patch_internal; that way the validation &
    # authorisation system has enough info to work.
    nodes_coll = current_app.data.driver.db['nodes']
    projection = {'user': 1,
                  'project': 1,
                  'node_type': 1}
    node = nodes_coll.find_one(node_id, projection=projection)
    if node is None:
        log.warning('User %s wanted to patch non-existing node %s' % (user_id, node_id))
        raise wz_exceptions.NotFound('Node %s not found' % node_id)

    if node['user'] != user_id and not authorization.user_has_role('admin'):
        raise wz_exceptions.Forbidden('You can only edit your own comments.')

    # Use Eve to PATCH this node, as that also updates the etag.
    r, _, _, status = patch_internal('nodes',
                                     {'properties.content': patch['content'],
                                      'project': node['project'],
                                      'user': node['user'],
                                      'node_type': node['node_type']},
                                     concurrency_check=False,
                                     _id=node_id)
    if status != 200:
        log.error('Error %i editing comment %s for user %s: %s',
                  status, node_id, user_id, r)
        raise wz_exceptions.InternalServerError('Internal error %i from Eve' % status)
    else:
        log.info('User %s edited comment %s', user_id, node_id)

    # Fetch the new content, so the client can show these without querying again.
    node = nodes_coll.find_one(node_id, projection={'properties.content_html': 1})
    return status, node


def assert_is_valid_patch(node_id, patch):
    """Raises an exception when the patch isn't valid."""

    try:
        op = patch['op']
    except KeyError:
        raise wz_exceptions.BadRequest("PATCH should have a key 'op' indicating the operation.")

    if op not in VALID_COMMENT_OPERATIONS:
        raise wz_exceptions.BadRequest('Operation should be one of %s',
                                       ', '.join(VALID_COMMENT_OPERATIONS))

    if op not in COMMENT_VOTING_OPS:
        # We can't check here, we need the node owner for that.
        return

    # See whether the user is allowed to patch
    if authorization.user_matches_roles(ROLES_FOR_COMMENT_VOTING):
        log.debug('User is allowed to upvote/downvote comment')
        return

    # Access denied.
    log.info('User %s wants to PATCH comment node %s, but is not allowed.',
             authentication.current_user_id(), node_id)
    raise wz_exceptions.Forbidden()
