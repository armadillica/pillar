import base64
import functools
import logging
import typing
import urllib.parse

import pymongo.errors
import werkzeug.exceptions as wz_exceptions
from bson import ObjectId
from flask import current_app, Blueprint, request

import pillar.markdown
from pillar.api.activities import activity_subscribe, activity_object_add
from pillar.api.node_types import PILLAR_NAMED_NODE_TYPES
from pillar.api.file_storage_backends.gcs import update_file_name
from pillar.api.utils import str2id, jsonify
from pillar.api.utils.authorization import check_permissions, require_login

log = logging.getLogger(__name__)
blueprint = Blueprint('nodes_api', __name__)
ROLES_FOR_SHARING = {'subscriber', 'demo'}


def only_for_node_type_decorator(*required_node_type_names):
    """Returns a decorator that checks its first argument's node type.

    If the node type is not of the required node type, returns None,
    otherwise calls the wrapped function.

    >>> deco = only_for_node_type_decorator('comment')
    >>> @deco
    ... def handle_comment(node): pass

    >>> deco = only_for_node_type_decorator('comment', 'post')
    >>> @deco
    ... def handle_comment_or_post(node): pass

    """

    # Convert to a set for efficient 'x in required_node_type_names' queries.
    required_node_type_names = set(required_node_type_names)

    def only_for_node_type(wrapped):
        @functools.wraps(wrapped)
        def wrapper(node, *args, **kwargs):
            if node.get('node_type') not in required_node_type_names:
                return

            return wrapped(node, *args, **kwargs)

        return wrapper

    only_for_node_type.__doc__ = "Decorator, immediately returns when " \
                                 "the first argument is not of type %s." % required_node_type_names
    return only_for_node_type


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

    return jsonify(short_link_info(short_code), status=status)


@blueprint.route('/tagged/')
@blueprint.route('/tagged/<tag>')
def tagged(tag=''):
    """Return all tagged nodes of public projects as JSON."""

    # We explicitly register the tagless endpoint to raise a 404, otherwise the PATCH
    # handler on /api/nodes/<node_id> will return a 405 Method Not Allowed.
    if not tag:
        raise wz_exceptions.NotFound()

    return _tagged(tag)


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
        {'$match': {'_project.is_private': False}},

        # Don't return the entire project for each node.
        {'$project': {'_project': False}},

        {'$sort': {'_created': -1}}
    ])
    return jsonify(list(agg))


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


def short_link_info(short_code):
    """Returns the short link info in a dict."""

    short_link = urllib.parse.urljoin(
        current_app.config['SHORT_LINK_BASE_URL'], short_code)

    return {
        'short_code': short_code,
        'short_link': short_link,
    }


def before_replacing_node(item, original):
    check_permissions('nodes', original, 'PUT')
    update_file_name(item)


def after_replacing_node(item, original):
    """Push an update to the Algolia index when a node item is updated. If the
    project is private, prevent public indexing.
    """

    from pillar.celery import search_index_tasks as index

    projects_collection = current_app.data.driver.db['projects']
    project = projects_collection.find_one({'_id': item['project']})
    if project.get('is_private', False):
        # Skip index updating and return
        return

    status = item['properties'].get('status', 'unpublished')
    node_id = str(item['_id'])

    if status == 'published':
        index.node_save.delay(node_id)
    else:
        index.node_delete.delay(node_id)


def before_inserting_nodes(items):
    """Before inserting a node in the collection we check if the user is allowed
    and we append the project id to it.
    """
    from pillar.auth import current_user

    nodes_collection = current_app.data.driver.db['nodes']

    def find_parent_project(node):
        """Recursive function that finds the ultimate parent of a node."""
        if node and 'parent' in node:
            parent = nodes_collection.find_one({'_id': node['parent']})
            return find_parent_project(parent)
        if node:
            return node
        else:
            return None

    for item in items:
        check_permissions('nodes', item, 'POST')
        if 'parent' in item and 'project' not in item:
            parent = nodes_collection.find_one({'_id': item['parent']})
            project = find_parent_project(parent)
            if project:
                item['project'] = project['_id']

        # Default the 'user' property to the current user.
        item.setdefault('user', current_user.user_id)


def after_inserting_nodes(items):
    for item in items:
        # Skip subscriptions for first level items (since the context is not a
        # node, but a project).
        # TODO: support should be added for mixed context
        if 'parent' not in item:
            return
        context_object_id = item['parent']
        if item['node_type'] == 'comment':
            nodes_collection = current_app.data.driver.db['nodes']
            parent = nodes_collection.find_one({'_id': item['parent']})
            # Always subscribe to the parent node
            activity_subscribe(item['user'], 'node', item['parent'])
            if parent['node_type'] == 'comment':
                # If the parent is a comment, we provide its own parent as
                # context. We do this in order to point the user to an asset
                # or group when viewing the notification.
                verb = 'replied'
                context_object_id = parent['parent']
                # Subscribe to the parent of the parent comment (post or group)
                activity_subscribe(item['user'], 'node', parent['parent'])
            else:
                activity_subscribe(item['user'], 'node', item['_id'])
                verb = 'commented'
        elif item['node_type'] in PILLAR_NAMED_NODE_TYPES:
            verb = 'posted'
            activity_subscribe(item['user'], 'node', item['_id'])
        else:
            # Don't automatically create activities for non-Pillar node types,
            # as we don't know what would be a suitable verb (among other things).
            continue

        activity_object_add(
            item['user'],
            verb,
            'node',
            item['_id'],
            'node',
            context_object_id
        )


def deduct_content_type(node_doc, original=None):
    """Deduct the content type from the attached file, if any."""

    if node_doc['node_type'] != 'asset':
        log.debug('deduct_content_type: called on node type %r, ignoring', node_doc['node_type'])
        return

    node_id = node_doc.get('_id')
    try:
        file_id = ObjectId(node_doc['properties']['file'])
    except KeyError:
        if node_id is None:
            # Creation of a file-less node is allowed, but updates aren't.
            return
        log.warning('deduct_content_type: Asset without properties.file, rejecting.')
        raise wz_exceptions.UnprocessableEntity('Missing file property for asset node')

    files = current_app.data.driver.db['files']
    file_doc = files.find_one({'_id': file_id},
                              {'content_type': 1})
    if not file_doc:
        log.warning('deduct_content_type: Node %s refers to non-existing file %s, rejecting.',
                    node_id, file_id)
        raise wz_exceptions.UnprocessableEntity('File property refers to non-existing file')

    # Guess the node content type from the file content type
    file_type = file_doc['content_type']
    if file_type.startswith('video/'):
        content_type = 'video'
    elif file_type.startswith('image/'):
        content_type = 'image'
    else:
        content_type = 'file'

    node_doc['properties']['content_type'] = content_type


def nodes_deduct_content_type(nodes):
    for node in nodes:
        deduct_content_type(node)


def before_returning_node(node):
    # Run validation process, since GET on nodes entry point is public
    check_permissions('nodes', node, 'GET', append_allowed_methods=True)

    # Embed short_link_info if the node has a short_code.
    short_code = node.get('short_code')
    if short_code:
        node['short_link'] = short_link_info(short_code)['short_link']


def before_returning_nodes(nodes):
    for node in nodes['_items']:
        before_returning_node(node)


def node_set_default_picture(node, original=None):
    """Uses the image of an image asset or colour map of texture node as picture."""

    if node.get('picture'):
        log.debug('Node %s already has a picture, not overriding', node.get('_id'))
        return

    node_type = node.get('node_type')
    props = node.get('properties', {})
    content = props.get('content_type')

    if node_type == 'asset' and content == 'image':
        image_file_id = props.get('file')
    elif node_type == 'texture':
        # Find the colour map, defaulting to the first image map available.
        image_file_id = None
        for image in props.get('files', []):
            if image_file_id is None or image.get('map_type') == 'color':
                image_file_id = image.get('file')
    else:
        log.debug('Not setting default picture on node type %s content type %s',
                  node_type, content)
        return

    if image_file_id is None:
        log.debug('Nothing to set the picture to.')
        return

    log.debug('Setting default picture for node %s to %s', node.get('_id'), image_file_id)
    node['picture'] = image_file_id


def nodes_set_default_picture(nodes):
    for node in nodes:
        node_set_default_picture(node)


def before_deleting_node(node: dict):
    check_permissions('nodes', node, 'DELETE')


def after_deleting_node(item):
    from pillar.celery import search_index_tasks as index
    index.node_delete.delay(str(item['_id']))


only_for_textures = only_for_node_type_decorator('texture')


@only_for_textures
def texture_sort_files(node, original=None):
    """Sort files alphabetically by map type, with colour map first."""

    try:
        files = node['properties']['files']
    except KeyError:
        return

    # Sort the map types alphabetically, ensuring 'color' comes first.
    as_dict = {f['map_type']: f for f in files}
    types = sorted(as_dict.keys(), key=lambda k: '\0' if k == 'color' else k)
    node['properties']['files'] = [as_dict[map_type] for map_type in types]


def textures_sort_files(nodes):
    for node in nodes:
        texture_sort_files(node)


def parse_markdown(node, original=None):
    import copy

    projects_collection = current_app.data.driver.db['projects']
    project = projects_collection.find_one({'_id': node['project']}, {'node_types': 1})
    # Query node type directly using the key
    node_type = next(nt for nt in project['node_types']
                     if nt['name'] == node['node_type'])

    # Create a copy to not overwrite the actual schema.
    schema = copy.deepcopy(current_app.config['DOMAIN']['nodes']['schema'])
    schema['properties'] = node_type['dyn_schema']

    def find_markdown_fields(schema, node):
        """Find and process all makrdown validated fields."""
        for k, v in schema.items():
            if not isinstance(v, dict):
                continue

            if v.get('validator') == 'markdown':
                # If there is a match with the validator: markdown pair, assign the sibling
                # property (following the naming convention _<property>_html)
                # the processed value.
                if k in node:
                    html = pillar.markdown.markdown(node[k])
                    field_name = pillar.markdown.cache_field_name(k)
                    node[field_name] = html
            if isinstance(node, dict) and k in node:
                find_markdown_fields(v, node[k])

    find_markdown_fields(schema, node)

    return 'ok'


def parse_markdowns(items):
    for item in items:
        parse_markdown(item)


def setup_app(app, url_prefix):
    global _tagged

    cached = app.cache.memoize(timeout=300)
    _tagged = cached(_tagged)

    from . import patch
    patch.setup_app(app, url_prefix=url_prefix)

    app.on_fetched_item_nodes += before_returning_node
    app.on_fetched_resource_nodes += before_returning_nodes

    app.on_replace_nodes += before_replacing_node
    app.on_replace_nodes += parse_markdown
    app.on_replace_nodes += texture_sort_files
    app.on_replace_nodes += deduct_content_type
    app.on_replace_nodes += node_set_default_picture
    app.on_replaced_nodes += after_replacing_node

    app.on_insert_nodes += before_inserting_nodes
    app.on_insert_nodes += parse_markdowns
    app.on_insert_nodes += nodes_deduct_content_type
    app.on_insert_nodes += nodes_set_default_picture
    app.on_insert_nodes += textures_sort_files
    app.on_inserted_nodes += after_inserting_nodes

    app.on_update_nodes += texture_sort_files

    app.on_delete_item_nodes += before_deleting_node
    app.on_deleted_item_nodes += after_deleting_node

    app.register_api_blueprint(blueprint, url_prefix=url_prefix)
