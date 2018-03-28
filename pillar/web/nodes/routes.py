import os
import json
import logging
from datetime import datetime

import pillarsdk
from pillarsdk import Node
from pillarsdk import Project
from pillarsdk.exceptions import ResourceNotFound
from pillarsdk.exceptions import ForbiddenAccess

from flask import Blueprint, current_app
from flask import redirect
from flask import render_template
from flask import url_for
from flask import request
from flask import jsonify
from flask import abort
from flask_login import current_user
from flask_wtf.csrf import validate_csrf

import werkzeug.exceptions as wz_exceptions
from wtforms import SelectMultipleField
from flask_login import login_required
from jinja2.exceptions import TemplateNotFound

from pillar.api.utils.authorization import check_permissions
from pillar.web.utils import caching
from pillar.markdown import markdown
from pillar.web.nodes.forms import get_node_form
from pillar.web.nodes.forms import process_node_form
from pillar.web.nodes.custom.storage import StorageNode
from pillar.web.projects.routes import project_update_nodes_list
from pillar.web.utils import get_file
from pillar.web.utils import attach_project_pictures
from pillar.web.utils.jstree import jstree_build_children, GROUP_NODES
from pillar.web.utils.jstree import jstree_build_from_node
from pillar.web.utils.forms import build_file_select_form
from pillar.web import system_util

from . import finders, attachments

blueprint = Blueprint('nodes', __name__)
log = logging.getLogger(__name__)


def get_node(node_id, user_id):
    api = system_util.pillar_api()
    node = Node.find(node_id + '/?embedded={"node_type":1}', api=api)
    return node.to_dict()


@blueprint.route("/<node_id>/jstree")
def jstree(node_id):
    """JsTree view.

    This return a lightweight version of the node, to be used by JsTree in the
    frontend. We have two possible cases:
    - https://pillar/<node_id>/jstree (construct the whole
      expanded tree starting from the node_id. Use only once)
    - https://pillar/<node_id>/jstree&children=1 (deliver the
      children of a node - use in the navigation of the tree)
    """

    # Get node with basic embedded data
    api = system_util.pillar_api()
    node = Node.find(node_id, {
        'projection': {
            'name': 1,
            'node_type': 1,
            'parent': 1,
            'project': 1,
            'properties.content_type': 1,
        }
    }, api=api)

    if request.args.get('children') != '1':
        return jsonify(items=jstree_build_from_node(node))

    if node.node_type == 'storage':
        storage = StorageNode(node)
        # Check if we specify a path within the storage
        path = request.args.get('path')
        # Generate the storage listing
        listing = storage.browse(path)
        # Inject the current node id in the response, so that JsTree can
        # expose the storage_node property and use it for further queries
        listing['storage_node'] = node._id
        if 'children' in listing:
            for child in listing['children']:
                child['storage_node'] = node._id
        return jsonify(listing)

    return jsonify(jstree_build_children(node))


@blueprint.route("/<node_id>/view")
def view(node_id, extra_template_args: dict=None):
    api = system_util.pillar_api()

    # Get node, we'll embed linked objects later.
    try:
        node = Node.find(node_id, api=api)
    except ResourceNotFound:
        return render_template('errors/404_embed.html')
    except ForbiddenAccess:
        return render_template('errors/403_embed.html')

    node_type_name = node.node_type

    if node_type_name == 'post' and not request.args.get('embed'):
        # Posts shouldn't be shown at this route (unless viewed embedded, tipically
        # after an edit. Redirect to the correct one.
        return redirect(url_for_node(node=node))

    # Set the default name of the template path based on the node name
    template_path = os.path.join('nodes', 'custom', node_type_name)
    # Set the default action for a template. By default is view and we override
    # it only if we are working storage nodes, where an 'index' is also possible
    template_action = 'view'

    def allow_link():
        """Helper function to cross check if the user is authenticated, and it
        is has the 'subscriber' role. Also, we check if the node has world GET
        permissions, which means it's free.
        """

        # Check if node permissions for the world exist (if node is free)
        if node.permissions and node.permissions.world:
            return 'GET' in node.permissions.world

        return current_user.has_cap('subscriber')

    link_allowed = allow_link()

    node_type_handlers = {
        'asset': _view_handler_asset,
        'storage': _view_handler_storage,
        'texture': _view_handler_texture,
        'hdri': _view_handler_hdri,
    }
    if node_type_name in node_type_handlers:
        handler = node_type_handlers[node_type_name]
        template_path, template_action = handler(node, template_path, template_action, link_allowed)
    # Fetch linked resources.
    node.picture = get_file(node.picture, api=api)
    node.user = node.user and pillarsdk.User.find(node.user, api=api)

    try:
        node.parent = node.parent and pillarsdk.Node.find(node.parent, api=api)
    except ForbiddenAccess:
        # This can happen when a node has world-GET, but the parent doesn't.
        node.parent = None

    # Get children
    children_projection = {'project': 1, 'name': 1, 'picture': 1, 'parent': 1,
                           'node_type': 1, 'properties.order': 1, 'properties.status': 1,
                           'user': 1, 'properties.content_type': 1}
    children_where = {'parent': node._id}

    if node_type_name in GROUP_NODES:
        children_where['properties.status'] = 'published'
        children_projection['permissions.world'] = 1
    else:
        children_projection['properties.files'] = 1
        children_projection['properties.is_tileable'] = 1

    try:
        children = Node.all({
            'projection': children_projection,
            'where': children_where,
            'sort': [('properties.order', 1), ('name', 1)]}, api=api)
    except ForbiddenAccess:
        return render_template('errors/403_embed.html')
    children = children._items

    for child in children:
        child.picture = get_file(child.picture, api=api)

    # Overwrite the file length by the biggest variation, if any.
    if node.file and node.file_variations:
        node.file.length = max(var.length for var in node.file_variations)

    if request.args.get('format') == 'json':
        node = node.to_dict()
        node['url_edit'] = url_for('nodes.edit', node_id=node['_id'])
        return jsonify({
            'node': node,
            'children': children.to_dict() if children else {},
            'parent': node['parent'] if 'parent' in node else {}
        })

    if 't' in request.args:
        template_path = os.path.join('nodes', 'custom', 'asset')
        template_action = 'view_theatre'

    template_path = '{0}/{1}_embed.html'.format(template_path, template_action)

    # Full override for AMP view
    if request.args.get('format') == 'amp':
        template_path = 'nodes/view_amp.html'

    write_access = 'PUT' in (node.allowed_methods or set())

    if extra_template_args is None:
        extra_template_args = {}
    try:
        return render_template(template_path,
                               node_id=node._id,
                               node=node,
                               parent=node.parent,
                               children=children,
                               config=current_app.config,
                               write_access=write_access,
                               api=api,
                               **extra_template_args)
    except TemplateNotFound:
        log.error('Template %s does not exist for node type %s', template_path, node_type_name)
        return render_template('nodes/error_type_not_found.html',
                               node_id=node._id,
                               node=node,
                               parent=node.parent,
                               children=children,
                               config=current_app.config,
                               write_access=write_access,
                               api=api,
                               **extra_template_args)


def _view_handler_asset(node, template_path, template_action, link_allowed):
    # Attach the file document to the asset node
    node_file = get_file(node.properties.file)
    node.file = node_file

    # Remove the link to the file if it's not allowed.
    if node_file and not link_allowed:
        node.file.link = None

    if node_file and node_file.content_type is not None:
        asset_type = node_file.content_type.split('/')[0]
    else:
        asset_type = None

    if asset_type == 'video':
        # Process video type and select video template
        if link_allowed:
            sources = []
            if node_file and node_file.variations:
                for f in node_file.variations:
                    sources.append({'type': f.content_type, 'src': f.link})
                    # Build a link that triggers download with proper filename
                    # TODO: move this to Pillar
                    if f.backend == 'cdnsun':
                        f.link = "{0}&name={1}.{2}".format(f.link, node.name, f.format)
            node.video_sources = sources
            node.file_variations = node_file.variations
        else:
            node.video_sources = None
            node.file_variations = None
    elif asset_type != 'image':
        # Treat it as normal file (zip, blend, application, etc)
        asset_type = 'file'

    template_path = os.path.join(template_path, asset_type)

    return template_path, template_action


def _view_handler_storage(node, template_path, template_action, link_allowed):
    storage = StorageNode(node)
    path = request.args.get('path')
    listing = storage.browse(path)
    node.name = listing['name']
    listing['storage_node'] = node._id
    # If the item has children we are working with a group
    if 'children' in listing:
        for child in listing['children']:
            child['storage_node'] = node._id
            child['name'] = child['text']
            child['content_type'] = os.path.dirname(child['type'])
        node.children = listing['children']
        template_action = 'index'
    else:
        node.status = 'published'
        node.length = listing['size']
        node.download_link = listing['signed_url']
    return template_path, template_action


def _view_handler_texture(node, template_path, template_action, link_allowed):
    for f in node.properties.files:
        f.file = get_file(f.file)
        # Remove the link to the file if it's not allowed.
        if f.file and not link_allowed:
            f.file.link = None

    return template_path, template_action


def _view_handler_hdri(node, template_path, template_action, link_allowed):
    if not link_allowed:
        node.properties.files = None
    else:
        for f in node.properties.files:
            f.file = get_file(f.file)

    return template_path, template_action


@blueprint.route('/<node_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(node_id):
    """Generic node editing form, displayed only if the user is allowed.
    """

    def set_properties(dyn_schema, form_schema, node_properties, form, set_data,
                       prefix=""):
        """Initialize custom properties for the form. We run this function once
        before validating the function with set_data=False, so that we can set
        any multiselect field that was originally specified empty and fill it
        with the current choices.
        """

        log.debug('set_properties(..., prefix=%r, set_data=%r) called', prefix, set_data)

        for prop, schema_prop in dyn_schema.items():
            prop_name = "{0}{1}".format(prefix, prop)

            if prop_name not in form:
                continue

            try:
                db_prop_value = node_properties[prop]
            except KeyError:
                log.debug('%s not found in form for node %s', prop_name, node_id)
                continue

            if schema_prop['type'] == 'datetime':
                db_prop_value = datetime.strptime(db_prop_value,
                                                  current_app.config['RFC1123_DATE_FORMAT'])

            if isinstance(form[prop_name], SelectMultipleField):
                # If we are dealing with a multiselect field, check if
                # it's empty (usually because we can't query the whole
                # database to pick all the choices). If it's empty we
                # populate the choices with the actual data.
                if not form[prop_name].choices:
                    form[prop_name].choices = [(d, d) for d in db_prop_value]
                    # Choices should be a tuple with value and name
            if not set_data:
                continue

            # Assign data to the field
            if prop_name == 'attachments':
                # If attachments is an empty list, do not append data
                if not db_prop_value:
                    continue
                attachments.attachment_form_group_set_data(db_prop_value, schema_prop,
                                                           form[prop_name])
            elif prop_name == 'files':
                subschema = schema_prop['schema']['schema']
                # Extra entries are caused by min_entries=1 in the form
                # creation.
                field_list = form[prop_name]
                if len(db_prop_value):
                    while len(field_list):
                        field_list.pop_entry()

                for file_data in db_prop_value:
                    file_form_class = build_file_select_form(subschema)
                    subform = file_form_class()
                    for key, value in file_data.items():
                        setattr(subform, key, value)
                    field_list.append_entry(subform)

            # elif prop_name == 'tags':
            #     form[prop_name].data = ', '.join(data)
            else:
                form[prop_name].data = db_prop_value

    api = system_util.pillar_api()
    node = Node.find(node_id, api=api)

    # We do not want to display the page to users who can't PUT
    if 'PUT' not in node.allowed_methods:
        raise wz_exceptions.Forbidden()

    project = Project.find(node.project, api=api)
    node_type = project.get_node_type(node.node_type)
    form = get_node_form(node_type)
    user_id = current_user.objectid
    dyn_schema = node_type['dyn_schema'].to_dict()
    form_schema = node_type['form_schema'].to_dict()
    error = ""
    node_properties = node.properties.to_dict()

    ensure_lists_exist_as_empty(node.to_dict(), node_type)
    set_properties(dyn_schema, form_schema, node_properties, form,
                   set_data=False)

    if form.validate_on_submit():
        if process_node_form(form, node_id=node_id, node_type=node_type, user=user_id):
            # Handle the specific case of a blog post
            if node_type.name == 'post':
                project_update_nodes_list(node, project_id=project._id, list_name='blog')
            else:
                try:
                    project_update_nodes_list(node, project_id=project._id)
                except ForbiddenAccess:
                    # TODO (fsiddi): Implement this as a blender-cloud-only hook
                    log.debug('User %s not allowed to update latest_nodes in %s' %
                              (user_id, project._id))
            return redirect(url_for('nodes.view', node_id=node_id, embed=1,
                                    _external=True,
                                    _scheme=current_app.config['SCHEME']))
        else:
            log.debug('Error sending data to Pillar, see Pillar logs.')
            error = 'Server error'
    else:
        if form.errors:
            log.debug('Form errors: %s', form.errors)
    # Populate Form
    form.name.data = node.name
    form.description.data = node.description
    if 'picture' in form:
        form.picture.data = node.picture
    if node.parent:
        form.parent.data = node.parent
    set_properties(dyn_schema, form_schema, node_properties, form, set_data=True)

    # Get previews
    node.picture = get_file(node.picture, api=api) if node.picture else None

    # Get Parent
    try:
        parent = Node.find(node['parent'], api=api)
    except KeyError:
        parent = None
    except ResourceNotFound:
        parent = None

    embed_string = ''
    # Check if we want to embed the content via an AJAX call
    if request.args.get('embed') == '1':
        # Define the prefix for the embedded template
        embed_string = '_embed'
    else:
        attach_project_pictures(project, api)

    template = 'nodes/custom/{0}/edit{1}.html'.format(node_type['name'], embed_string)
    # We should more simply check if the template file actually exists on the filesystem
    try:
        return render_template(
            template,
            node=node,
            parent=parent,
            form=form,
            errors=form.errors,
            error=error,
            api=api,
            project=project,)
    except TemplateNotFound:
        template = 'nodes/edit{1}.html'.format(node_type['name'], embed_string)
        is_embedded_edit = True if embed_string else False
        return render_template(
            template,
            node=node,
            parent=parent,
            form=form,
            errors=form.errors,
            error=error,
            api=api,
            project=project,
            is_embedded_edit=is_embedded_edit,
        )


@blueprint.route('/preview-markdown', methods=['POST'])
@login_required
def preview_markdown():
    """Return the 'content' field of POST request as HTML.

    This endpoint can be called via AJAX in order to preview the
    content of a node.
    """

    current_app.csrf.protect()

    try:
        content = request.form['content']
    except KeyError:
        return jsonify({'_status': 'ERR',
                        'message': 'The field "content" was not specified.'}), 400
    return jsonify(content=markdown(content))


def ensure_lists_exist_as_empty(node_doc, node_type):
    """Ensures that any properties of type 'list' exist as empty lists.

    This allows us to iterate over lists without worrying that they
    are set to None. Only works for top-level list properties.
    """

    node_properties = node_doc.setdefault('properties', {})

    for prop, schema in node_type.dyn_schema.to_dict().items():
        if schema['type'] != 'list':
            continue

        if node_properties.get(prop) is None:
            node_properties[prop] = []


@blueprint.route('/create', methods=['POST'])
@login_required
def create():
    """Create a node. Requires a number of params:

    - project id
    - node_type
    - parent node (optional)
    """
    if request.method != 'POST':
        return abort(403)

    project_id = request.form['project_id']
    parent_id = request.form.get('parent_id')
    node_type_name = request.form['node_type_name']

    api = system_util.pillar_api()
    # Fetch the Project or 404
    try:
        project = Project.find(project_id, api=api)
    except ResourceNotFound:
        return abort(404)

    node_type = project.get_node_type(node_type_name)
    node_type_name = 'folder' if node_type['name'] == 'group' else \
        node_type['name']

    node_props = dict(
        name='New {}'.format(node_type_name),
        project=project['_id'],
        user=current_user.objectid,
        node_type=node_type['name'],
        properties={}
    )

    if parent_id:
        node_props['parent'] = parent_id

    ensure_lists_exist_as_empty(node_props, node_type)

    node = Node(node_props)
    node.create(api=api)

    return jsonify(status='success', data=dict(asset_id=node['_id']))


@blueprint.route("/<node_id>/redir")
def redirect_to_context(node_id):
    """Redirects to the context URL of the node.

    Comment: redirects to whatever the comment is attached to + #node_id
        (unless 'whatever the comment is attached to' already contains '#', then
         '#node_id' isn't appended)
    Post: redirects to main or project-specific blog post
    Other: redirects to project.url + #node_id
    """

    if node_id.lower() == '{{objectid}}':
        log.warning("JavaScript should have filled in the ObjectID placeholder, but didn't. "
                    "URL=%s and referrer=%s",
                    request.url, request.referrer)
        raise wz_exceptions.NotFound('Invalid ObjectID')

    try:
        url = url_for_node(node_id)
    except ValueError as ex:
        log.warning("%s: URL=%s and referrer=%s",
                    str(ex), request.url, request.referrer)
        raise wz_exceptions.NotFound('Invalid ObjectID')

    return redirect(url)


def url_for_node(node_id=None, node=None):
    assert isinstance(node_id, (str, type(None)))

    api = system_util.pillar_api()

    if node_id is None and node is None:
        raise ValueError('Either node or node_id must be given')

    if node is None:
        try:
            node = Node.find(node_id, api=api)
        except ResourceNotFound:
            log.warning(
                'url_for_node(node_id=%r, node=None): Unable to find node.',
                node_id)
            raise wz_exceptions.NotFound('Unable to find node %r' % node_id)

    return finders.find_url_for_node(node)


# Import of custom modules (using the same nodes decorator)
from .custom import comments, groups, storage, posts
