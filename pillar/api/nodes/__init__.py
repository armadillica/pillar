import base64
import datetime
import logging

import pymongo.errors
import werkzeug.exceptions as wz_exceptions
from flask import current_app, Blueprint, request

from pillar.api.nodes import eve_hooks, comments
from pillar.api.utils import str2id, jsonify
from pillar.api.utils.authorization import check_permissions, require_login
from pillar.web.utils import pretty_date

log = logging.getLogger(__name__)
blueprint = Blueprint('nodes_api', __name__)
ROLES_FOR_SHARING = ROLES_FOR_COMMENTING ={'subscriber', 'demo'}


@blueprint.route('/<node_id>/share', methods=['GET', 'POST'])
@require_login(require_roles=ROLES_FOR_SHARING)
def share_node(node_id):
    """Shares a node, or returns sharing information."""

    node_id = str2id(node_id)
    nodes_coll = current_app.data.driver.db['nodes']

    node = nodes_coll.find_one({'_id': node_id},
                               projection={
                                   'project': 1,
                                   'node_type': 1,
                                   'short_code': 1
                               })
    if not node:
        raise wz_exceptions.NotFound('Node %s does not exist.' % node_id)

    check_permissions('nodes', node, request.method)

    log.info('Sharing node %s', node_id)

    short_code = node.get('short_code')
    status = 200

    if not short_code:
        if request.method == 'POST':
            short_code = generate_and_store_short_code(node)
            make_world_gettable(node)
            status = 201
        else:
            return '', 204

    return jsonify(eve_hooks.short_link_info(short_code), status=status)


@blueprint.route('/<string(length=24):node_path>/comments', methods=['GET'])
def get_node_comments(node_path: str):
    node_id = str2id(node_path)
    return comments.get_node_comments(node_id)


@blueprint.route('/<string(length=24):node_path>/comments', methods=['POST'])
@require_login(require_roles=ROLES_FOR_COMMENTING)
def post_node_comment(node_path: str):
    node_id = str2id(node_path)
    msg = request.json['msg']
    attachments = request.json.get('attachments', {})
    return comments.post_node_comment(node_id, msg, attachments)


@blueprint.route('/<string(length=24):node_path>/comments/<string(length=24):comment_path>', methods=['PATCH'])
@require_login(require_roles=ROLES_FOR_COMMENTING)
def patch_node_comment(node_path: str, comment_path: str):
    node_id = str2id(node_path)
    comment_id = str2id(comment_path)
    msg = request.json['msg']
    attachments = request.json.get('attachments', {})
    return comments.patch_node_comment(node_id, comment_id, msg, attachments)


@blueprint.route('/<string(length=24):node_path>/comments/<string(length=24):comment_path>/vote', methods=['POST'])
@require_login(require_roles=ROLES_FOR_COMMENTING)
def post_node_comment_vote(node_path: str, comment_path: str):
    node_id = str2id(node_path)
    comment_id = str2id(comment_path)
    vote_str = request.json['vote']
    vote = int(vote_str)
    return comments.post_node_comment_vote(node_id, comment_id, vote)


@blueprint.route('/tagged/')
@blueprint.route('/tagged/<tag>')
def tagged(tag=''):
    """Return all tagged nodes of public projects as JSON."""
    from pillar.auth import current_user

    # We explicitly register the tagless endpoint to raise a 404, otherwise the PATCH
    # handler on /api/nodes/<node_id> will return a 405 Method Not Allowed.
    if not tag:
        raise wz_exceptions.NotFound()

    # Build the (cached) list of tagged nodes
    agg_list = _tagged(tag)

    for node in agg_list:
        if node['properties'].get('duration_seconds'):
            node['properties']['duration'] = datetime.timedelta(seconds=node['properties']['duration_seconds'])

        if node.get('_created') is not None:
            node['pretty_created'] = pretty_date(node['_created'])

    # If the user is anonymous, no more information is needed and we return
    if current_user.is_anonymous:
        return jsonify(agg_list)

    # If the user is authenticated, attach view_progress for video assets
    view_progress = current_user.nodes['view_progress']
    for node in agg_list:
        node_id = str(node['_id'])
        # View progress should be added only for nodes of type 'asset' and
        # with content_type 'video', only if the video was already in the watched
        # list for the current user.
        if node_id in view_progress:
            node['view_progress'] = view_progress[node_id]

    return jsonify(agg_list)


def _tagged(tag: str):
    """Fetch all public nodes with the given tag.

    This function is cached, see setup_app().
    """
    nodes_coll = current_app.db('nodes')
    agg = nodes_coll.aggregate([
        {'$match': {'properties.tags': tag,
                    '_deleted': {'$ne': True}}},

        # Only get nodes from public projects. This is done after matching the
        # tagged nodes, because most likely nobody else will be able to tag
        # nodes anyway.
        {'$lookup': {
            'from': 'projects',
            'localField': 'project',
            'foreignField': '_id',
            'as': '_project',
        }},
        {'$unwind': '$_project'},
        {'$match': {'_project.is_private': False}},
        {'$addFields': {
            'project._id': '$_project._id',
            'project.name': '$_project.name',
            'project.url': '$_project.url',
        }},

        # Don't return the entire project/file for each node.
        {'$project': {'_project': False}},
        {'$sort': {'_created': -1}}
    ])

    return list(agg)


def generate_and_store_short_code(node):
    nodes_coll = current_app.data.driver.db['nodes']
    node_id = node['_id']

    log.debug('Creating new short link for node %s', node_id)

    max_attempts = 10
    for attempt in range(1, max_attempts):

        # Generate a new short code
        short_code = create_short_code(node)
        log.debug('Created short code for node %s: %s', node_id, short_code)

        node['short_code'] = short_code

        # Store it in MongoDB
        try:
            result = nodes_coll.update_one({'_id': node_id},
                                           {'$set': {'short_code': short_code}})
            break
        except pymongo.errors.DuplicateKeyError:
            log.info('Duplicate key while creating short code, retrying (attempt %i/%i)',
                     attempt, max_attempts)
            pass
    else:
        log.error('Unable to find unique short code for node %s after %i attempts, failing!',
                  node_id, max_attempts)
        raise wz_exceptions.InternalServerError('Unable to create unique short code for node %s' %
                                                node_id)

    # We were able to store a short code, now let's verify the result.
    if result.matched_count != 1:
        log.warning('Unable to update node %s with new short_links=%r', node_id, node['short_code'])
        raise wz_exceptions.InternalServerError('Unable to update node %s with new short links' %
                                                node_id)

    return short_code


def make_world_gettable(node):
    nodes_coll = current_app.data.driver.db['nodes']
    node_id = node['_id']

    log.debug('Ensuring the world can read node %s', node_id)

    world_perms = set(node.get('permissions', {}).get('world', []))
    world_perms.add('GET')
    world_perms = list(world_perms)

    result = nodes_coll.update_one({'_id': node_id},
                                   {'$set': {'permissions.world': world_perms}})

    if result.matched_count != 1:
        log.warning('Unable to update node %s with new permissions.world=%r', node_id, world_perms)
        raise wz_exceptions.InternalServerError('Unable to update node %s with new permissions' %
                                                node_id)


def create_short_code(node) -> str:
    """Generates a new 'short code' for the node."""

    import secrets

    length = current_app.config['SHORT_CODE_LENGTH']

    # Base64 encoding will expand it a bit, so we'll cut that off later.
    # It's a good idea to start with enough bytes, though.
    bits = secrets.token_bytes(length)

    short_code = base64.b64encode(bits, altchars=b'xy').rstrip(b'=')
    short_code = short_code[:length].decode('ascii')

    return short_code


def setup_app(app, url_prefix):
    global _tagged

    cached = app.cache.memoize(timeout=300)
    _tagged = cached(_tagged)

    from . import patch
    patch.setup_app(app, url_prefix=url_prefix)

    app.on_fetched_item_nodes += eve_hooks.before_returning_node
    app.on_fetched_resource_nodes += eve_hooks.before_returning_nodes

    app.on_replace_nodes += eve_hooks.before_replacing_node
    app.on_replace_nodes += eve_hooks.texture_sort_files
    app.on_replace_nodes += eve_hooks.deduct_content_type_and_duration
    app.on_replace_nodes += eve_hooks.node_set_default_picture
    app.on_replaced_nodes += eve_hooks.after_replacing_node

    app.on_insert_nodes += eve_hooks.before_inserting_nodes
    app.on_insert_nodes += eve_hooks.nodes_deduct_content_type_and_duration
    app.on_insert_nodes += eve_hooks.nodes_set_default_picture
    app.on_insert_nodes += eve_hooks.textures_sort_files
    app.on_inserted_nodes += eve_hooks.after_inserting_nodes

    app.on_update_nodes += eve_hooks.texture_sort_files

    app.on_delete_item_nodes += eve_hooks.before_deleting_node
    app.on_deleted_item_nodes += eve_hooks.after_deleting_node

    app.register_api_blueprint(blueprint, url_prefix=url_prefix)
