import json
import logging

from pillarsdk import Node
from pillarsdk import Project
from pillarsdk.exceptions import ResourceNotFound
from pillarsdk.exceptions import ForbiddenAccess
from flask import Blueprint, current_app
from flask import render_template
from flask import request
from flask import jsonify
from flask import session
from flask import abort
from flask import redirect
from flask import url_for
from flask.ext.login import login_required
from flask.ext.login import current_user
import werkzeug.exceptions as wz_exceptions

from pillar.web import system_util
from pillar.web import utils
from pillar.web.utils.jstree import jstree_get_children
from .forms import ProjectForm
from .forms import NodeTypeForm

blueprint = Blueprint('projects', __name__)
log = logging.getLogger(__name__)
SYNC_GROUP_NODE_NAME = 'Blender Sync'
IMAGE_SHARING_GROUP_NODE_NAME = 'Image sharing'


@blueprint.route('/')
@login_required
def index():
    api = system_util.pillar_api()

    # Get all projects, except the home project.
    projects_user = Project.all({
        'where': {'user': current_user.objectid,
                  'category': {'$ne': 'home'}},
        'sort': '-_created'
    }, api=api)

    projects_shared = Project.all({
        'where': {'user': {'$ne': current_user.objectid},
                  'permissions.groups.group': {'$in': current_user.groups},
                  'is_private': True},
        'sort': '-_created',
        'embedded': {'user': 1},
    }, api=api)

    # Attach project images
    for project in projects_user['_items']:
        utils.attach_project_pictures(project, api)

    for project in projects_shared['_items']:
        utils.attach_project_pictures(project, api)

    return render_template(
        'projects/index_dashboard.html',
        gravatar=utils.gravatar(current_user.email, size=128),
        projects_user=projects_user['_items'],
        projects_shared=projects_shared['_items'],
        api=api)


@blueprint.route('/<project_url>/jstree')
def jstree(project_url):
    """Entry point to view a project as JSTree"""
    api = system_util.pillar_api()

    try:
        project = Project.find_one({
            'projection': {'_id': 1},
            'where': {'url': project_url}
        }, api=api)
    except ResourceNotFound:
        raise wz_exceptions.NotFound('No such project')

    return jsonify(items=jstree_get_children(None, project._id))


@blueprint.route('/home/')
@login_required
def home_project():
    api = system_util.pillar_api()
    project = _home_project(api)

    # Get the synchronised Blender versions
    project_id = project['_id']
    synced_versions = synced_blender_versions(project_id, api)

    extra_context = {
        'synced_versions': synced_versions,
        'show_addon_download_buttons': True,
    }

    return render_project(project, api, extra_context)


@blueprint.route('/home/images')
@login_required
def home_project_shared_images():
    api = system_util.pillar_api()
    project = _home_project(api)

    # Get the shared images
    project_id = project['_id']
    image_nodes = shared_image_nodes(project_id, api)

    extra_context = {
        'shared_images': image_nodes,
        'show_addon_download_buttons': current_user.has_role('subscriber', 'demo'),
    }

    return render_project(project, api, extra_context,
                          template_name='projects/home_images.html')


def _home_project(api):
    try:
        project = Project.find_from_endpoint('/bcloud/home-project', api=api)
    except ResourceNotFound:
        log.warning('Home project for user %s not found', current_user.objectid)
        raise wz_exceptions.NotFound('No such project')

    return project


def synced_blender_versions(home_project_id, api):
    """Returns a list of Blender versions with synced settings.

    Returns a list of {'version': '2.77', 'date': datetime.datetime()} dicts.
    Returns an empty list if no Blender versions were synced.
    """

    sync_group = Node.find_first({
        'where': {'project': home_project_id,
                  'node_type': 'group',
                  'parent': None,
                  'name': SYNC_GROUP_NODE_NAME},
        'projection': {'_id': 1}},
        api=api)

    if not sync_group:
        return []

    sync_nodes = Node.all({
        'where': {'project': home_project_id,
                  'node_type': 'group',
                  'parent': sync_group['_id']},
        'projection': {
            'name': 1,
            '_updated': 1,
        }},
        api=api)

    sync_nodes = sync_nodes._items
    if not sync_nodes:
        return []

    return [{'version': node.name, 'date': node._updated}
            for node in sync_nodes]


def shared_image_nodes(home_project_id, api):
    """Returns a list of pillarsdk.Node objects."""

    parent_group = Node.find_first({
        'where': {'project': home_project_id,
                  'node_type': 'group',
                  'parent': None,
                  'name': IMAGE_SHARING_GROUP_NODE_NAME},
        'projection': {'_id': 1}},
        api=api)

    if not parent_group:
        log.debug('No image sharing parent node found.')
        return []

    nodes = Node.all({
        'where': {'project': home_project_id,
                  'node_type': 'asset',
                  'properties.content_type': 'image',
                  'parent': parent_group['_id']},
        'sort': '-_created',
        'projection': {
            '_created': 1,
            'name': 1,
            'picture': 1,
            'short_code': 1,
        }},
        api=api)

    nodes = nodes._items or []
    for node in nodes:
        node.picture = utils.get_file(node.picture)

    return nodes


@blueprint.route('/home/jstree')
def home_jstree():
    """Entry point to view the home project as JSTree"""
    api = system_util.pillar_api()

    try:
        project = Project.find_from_endpoint('/bcloud/home-project',
                                             params={'projection': {
                                                 '_id': 1,
                                                 'permissions': 1,
                                                 'category': 1,
                                                 'user': 1}},
                                             api=api)
    except ResourceNotFound:
        raise wz_exceptions.NotFound('No such project')

    return jsonify(items=jstree_get_children(None, project._id))


@blueprint.route('/<project_url>/')
def view(project_url):
    """Entry point to view a project"""

    if request.args.get('format') == 'jstree':
        log.warning('projects.view(%r) endpoint called with format=jstree, '
                    'redirecting to proper endpoint. URL is %s; referrer is %s',
                    project_url, request.url, request.referrer)
        return redirect(url_for('projects.jstree', project_url=project_url))

    api = system_util.pillar_api()
    project = find_project_or_404(project_url,
                                  embedded={'header_node': 1},
                                  api=api)

    # Load the header video file, if there is any.
    header_video_file = None
    header_video_node = None
    if project.header_node and project.header_node.node_type == 'asset' and \
                    project.header_node.properties.content_type == 'video':
            header_video_node = project.header_node
            header_video_file = utils.get_file(project.header_node.properties.file)
            header_video_node.picture = utils.get_file(header_video_node.picture)

    return render_project(project, api,
                          extra_context={'header_video_file': header_video_file,
                                         'header_video_node': header_video_node})


def render_project(project, api, extra_context=None, template_name=None):
    project.picture_square = utils.get_file(project.picture_square, api=api)
    project.picture_header = utils.get_file(project.picture_header, api=api)

    def load_latest(list_of_ids, get_picture=False):
        """Loads a list of IDs in reversed order."""

        if not list_of_ids:
            return []

        # Construct query parameters outside the loop.
        projection = {'name': 1, 'user': 1, 'node_type': 1, 'project': 1, 'properties.url': 1}
        params = {'projection': projection, 'embedded': {'user': 1}}
        if get_picture:
            projection['picture'] = 1

        list_latest = []
        for node_id in reversed(list_of_ids or ()):
            try:
                node_item = Node.find(node_id, params, api=api)

                node_item.picture = utils.get_file(node_item.picture, api=api)
                list_latest.append(node_item)
            except ForbiddenAccess:
                pass
            except ResourceNotFound:
                log.warning('Project %s refers to removed node %s!',
                            project._id, node_id)

        return list_latest

    project.nodes_latest = load_latest(project.nodes_latest)
    project.nodes_featured = load_latest(project.nodes_featured, get_picture=True)
    project.nodes_blog = load_latest(project.nodes_blog)

    if extra_context is None:
        extra_context = {}

    if project.category == 'home' and not current_app.config['RENDER_HOME_AS_REGULAR_PROJECT']:
        template_name = template_name or 'projects/home_index.html'
        return render_template(
            template_name,
            gravatar=utils.gravatar(current_user.email, size=128),
            project=project,
            api=system_util.pillar_api(),
            **extra_context)

    if template_name is None:
        if request.args.get('embed'):
            embed_string = '_embed'
        else:
            embed_string = ''
        template_name = "projects/view{0}.html".format(embed_string)

    return render_template(template_name,
                           api=api,
                           project=project,
                           node=None,
                           show_node=False,
                           show_project=True,
                           og_picture=project.picture_header,
                           **extra_context)


@blueprint.route('/<project_url>/<node_id>')
def view_node(project_url, node_id):
    """Entry point to view a node in the context of a project"""

    # Some browsers mangle URLs and URL-encode /p/{p-url}/#node-id
    if node_id.startswith('#'):
        return redirect(url_for('projects.view_node',
                                project_url=project_url,
                                node_id=node_id[1:]),
                        code=301)  # permanent redirect

    if not utils.is_valid_id(node_id):
        raise wz_exceptions.NotFound('No such node')

    api = system_util.pillar_api()
    theatre_mode = 't' in request.args

    # Fetch the node before the project. If this user has access to the
    # node, we should be able to get the project URL too.
    try:
        node = Node.find(node_id, api=api)
    except ForbiddenAccess:
        return render_template('errors/403.html'), 403
    except ResourceNotFound:
        raise wz_exceptions.NotFound('No such node')

    try:
        project = Project.find_one({'where': {"url": project_url, '_id': node.project}}, api=api)
    except ResourceNotFound:
        # In theatre mode, we don't need access to the project at all.
        if theatre_mode:
            project = None
        else:
            raise wz_exceptions.NotFound('No such project')

    og_picture = node.picture = utils.get_file(node.picture, api=api)
    if project:
        if not node.picture:
            og_picture = utils.get_file(project.picture_header, api=api)
        project.picture_square = utils.get_file(project.picture_square, api=api)

    # Append _theatre to load the proper template
    theatre = '_theatre' if theatre_mode else ''

    return render_template('projects/view{}.html'.format(theatre),
                           api=api,
                           project=project,
                           node=node,
                           show_node=True,
                           show_project=False,
                           og_picture=og_picture)


def find_project_or_404(project_url, embedded=None, api=None):
    """Aborts with a NotFound exception when the project cannot be found."""

    params = {'where': {"url": project_url}}
    if embedded:
        params['embedded'] = embedded

    try:
        project = Project.find_one(params, api=api)
    except ResourceNotFound:
        raise wz_exceptions.NotFound('No such project')

    return project


@blueprint.route('/<project_url>/search')
def search(project_url):
    """Search into a project"""
    api = system_util.pillar_api()
    project = find_project_or_404(project_url, api=api)
    project.picture_square = utils.get_file(project.picture_square, api=api)
    project.picture_header = utils.get_file(project.picture_header, api=api)

    return render_template('nodes/search.html',
                           project=project,
                           og_picture=project.picture_header)


@blueprint.route('/<project_url>/about')
def about(project_url):
    """About page of a project"""

    # TODO: Duplicated code from view function, we could re-use view instead

    api = system_util.pillar_api()
    project = find_project_or_404(project_url,
                                  embedded={'header_node': 1},
                                  api=api)

    # Load the header video file, if there is any.
    header_video_file = None
    header_video_node = None
    if project.header_node and project.header_node.node_type == 'asset' and \
                    project.header_node.properties.content_type == 'video':
            header_video_node = project.header_node
            header_video_file = utils.get_file(project.header_node.properties.file)
            header_video_node.picture = utils.get_file(header_video_node.picture)

    return render_project(project, api,
                          extra_context={'title': 'about',
                                         'header_video_file': header_video_file,
                                         'header_video_node': header_video_node})


@blueprint.route('/<project_url>/edit', methods=['GET', 'POST'])
@login_required
def edit(project_url):
    api = system_util.pillar_api()
    # Fetch the Node or 404
    try:
        project = Project.find_one({'where': {'url': project_url}}, api=api)
        # project = Project.find(project_url, api=api)
    except ResourceNotFound:
        abort(404)
    utils.attach_project_pictures(project, api)
    form = ProjectForm(
        project_id=project._id,
        name=project.name,
        url=project.url,
        summary=project.summary,
        description=project.description,
        is_private=u'GET' not in project.permissions.world,
        category=project.category,
        status=project.status,
    )

    if form.validate_on_submit():
        project = Project.find(project._id, api=api)
        project.name = form.name.data
        project.url = form.url.data
        project.summary = form.summary.data
        project.description = form.description.data
        project.category = form.category.data
        project.status = form.status.data
        if form.picture_square.data:
            project.picture_square = form.picture_square.data
        if form.picture_header.data:
            project.picture_header = form.picture_header.data

        # Update world permissions from is_private checkbox
        if form.is_private.data:
            project.permissions.world = []
        else:
            project.permissions.world = [u'GET']

        project.update(api=api)
        # Reattach the pictures
        utils.attach_project_pictures(project, api)
    else:
        if project.picture_square:
            form.picture_square.data = project.picture_square._id
        if project.picture_header:
            form.picture_header.data = project.picture_header._id

    # List of fields from the form that should be hidden to regular users
    if current_user.has_role('admin'):
        hidden_fields = []
    else:
        hidden_fields = ['url', 'status', 'is_private', 'category']

    return render_template('projects/edit.html',
                           form=form,
                           hidden_fields=hidden_fields,
                           project=project,
                           api=api)


@blueprint.route('/<project_url>/edit/node-type')
@login_required
def edit_node_types(project_url):
    api = system_util.pillar_api()
    # Fetch the project or 404
    try:
        project = Project.find_one({
            'where': '{"url" : "%s"}' % (project_url)}, api=api)
    except ResourceNotFound:
        return abort(404)

    utils.attach_project_pictures(project, api)

    return render_template('projects/edit_node_types.html',
                           api=api,
                           project=project)


@blueprint.route('/<project_url>/e/node-type/<node_type_name>', methods=['GET', 'POST'])
@login_required
def edit_node_type(project_url, node_type_name):
    api = system_util.pillar_api()
    # Fetch the Node or 404
    try:
        project = Project.find_one({
            'where': '{"url" : "%s"}' % (project_url)}, api=api)
    except ResourceNotFound:
        return abort(404)
    utils.attach_project_pictures(project, api)
    node_type = project.get_node_type(node_type_name)
    form = NodeTypeForm()
    if form.validate_on_submit():
        # Update dynamic & form schemas
        dyn_schema = json.loads(form.dyn_schema.data)
        node_type.dyn_schema = dyn_schema
        form_schema = json.loads(form.form_schema.data)
        node_type.form_schema = form_schema

        # Update permissions
        permissions = json.loads(form.permissions.data)
        node_type.permissions = permissions

        project.update(api=api)
    elif request.method == 'GET':
        form.project_id.data = project._id
        if node_type:
            form.name.data = node_type.name
            form.description.data = node_type.description
            form.parent.data = node_type.parent

            dyn_schema = node_type.dyn_schema.to_dict()
            form_schema = node_type.form_schema.to_dict()
            if 'permissions' in node_type:
                permissions = node_type.permissions.to_dict()
            else:
                permissions = {}

            form.form_schema.data = json.dumps(form_schema, indent=4)
            form.dyn_schema.data = json.dumps(dyn_schema, indent=4)
            form.permissions.data = json.dumps(permissions, indent=4)
    return render_template('projects/edit_node_type.html',
                           form=form,
                           project=project,
                           api=api,
                           node_type=node_type)


@blueprint.route('/<project_url>/edit/sharing', methods=['GET', 'POST'])
@login_required
def sharing(project_url):
    api = system_util.pillar_api()
    # Fetch the project or 404
    try:
        project = Project.find_one({
            'where': '{"url" : "%s"}' % (project_url)}, api=api)
    except ResourceNotFound:
        return abort(404)

    # Fetch users that are part of the admin group
    users = project.get_users(api=api)
    for user in users['_items']:
        user['avatar'] = utils.gravatar(user['email'])

    if request.method == 'POST':
        user_id = request.form['user_id']
        action = request.form['action']
        try:
            if action == 'add':
                user = project.add_user(user_id, api=api)
            elif action == 'remove':
                user = project.remove_user(user_id, api=api)
        except ResourceNotFound:
            log.info('/p/%s/edit/sharing: User %s not found', project_url, user_id)
            return jsonify({'_status': 'ERROR',
                            'message': 'User %s not found' % user_id}), 404

        # Add gravatar to user
        user['avatar'] = utils.gravatar(user['email'])
        return jsonify(user)

    utils.attach_project_pictures(project, api)

    return render_template('projects/sharing.html',
                           api=api,
                           project=project,
                           users=users['_items'])


@blueprint.route('/e/add-featured-node', methods=['POST'])
@login_required
def add_featured_node():
    """Feature a node in a project. This method belongs here, because it affects
    the project node itself, not the asset.
    """
    api = system_util.pillar_api()
    node = Node.find(request.form['node_id'], api=api)
    action = project_update_nodes_list(node, project_id=node.project, list_name='featured')
    return jsonify(status='success', data=dict(action=action))


@blueprint.route('/e/move-node', methods=['POST'])
@login_required
def move_node():
    """Move a node within a project. While this affects the node.parent prop, we
    keep it in the scope of the project."""
    node_id = request.form['node_id']
    dest_parent_node_id = request.form.get('dest_parent_node_id')

    api = system_util.pillar_api()
    node = Node.find(node_id, api=api)
    # Get original parent id for clearing template fragment on success
    previous_parent_id = node.parent
    if dest_parent_node_id:
        node.parent = dest_parent_node_id
    elif node.parent:
        node.parent = None
    node.update(api=api)
    return jsonify(status='success', data=dict(message='node moved'))


@blueprint.route('/e/delete-node', methods=['POST'])
@login_required
def delete_node():
    """Delete a node"""
    api = system_util.pillar_api()
    node = Node.find(request.form['node_id'], api=api)
    if not node.has_method('DELETE'):
        return abort(403)

    node.delete(api=api)

    return jsonify(status='success', data=dict(message='Node deleted'))


@blueprint.route('/e/toggle-node-public', methods=['POST'])
@login_required
def toggle_node_public():
    """Give a node GET permissions for the world. Later on this can turn into
    a more powerful permission management function.
    """
    api = system_util.pillar_api()
    node = Node.find(request.form['node_id'], api=api)
    if node.has_method('PUT'):
        if node.permissions and 'world' in node.permissions.to_dict():
            node.permissions = {}
            message = "Node is not public anymore."
        else:
            node.permissions = dict(world=['GET'])
            message = "Node is now public!"
        node.update(api=api)
        return jsonify(status='success', data=dict(message=message))
    else:
        return abort(403)


@blueprint.route('/e/toggle-node-project-header', methods=['POST'])
@login_required
def toggle_node_project_header():
    """Sets this node as the project header, or removes it if already there.
    """

    api = system_util.pillar_api()
    node_id = request.form['node_id']

    try:
        node = Node.find(node_id, {'projection': {'project': 1}}, api=api)
    except ResourceNotFound:
        log.info('User %s trying to toggle non-existing node %s as project header',
                 current_user.objectid, node_id)
        return jsonify(_status='ERROR', message='Node not found'), 404

    try:
        project = Project.find(node.project, api=api)
    except ResourceNotFound:
        log.info('User %s trying to toggle node %s as project header, but project %s not found',
                 current_user.objectid, node_id, node.project)
        return jsonify(_status='ERROR', message='Project not found'), 404

    # Toggle header node
    if project.header_node == node_id:
        log.debug('Un-setting header node of project %s', node.project)
        project.header_node = None
        action = 'unset'
    else:
        log.debug('Setting node %s as header of project %s', node_id, node.project)
        project.header_node = node_id
        action = 'set'

    # Save the project
    project.update(api=api)

    return jsonify({'_status': 'OK',
                    'action': action})


def project_update_nodes_list(node, project_id=None, list_name='latest'):
    """Update the project node with the latest edited or favorited node.
    The list value can be 'latest' or 'featured' and it will determined where
    the node reference will be placed in.
    """
    if node.properties.status and node.properties.status == 'published':
        if not project_id and 'current_project_id' in session:
            project_id = session['current_project_id']
        elif not project_id:
            return None
        project_id = node.project
        if type(project_id) is not unicode:
            project_id = node.project._id
        api = system_util.pillar_api()
        project = Project.find(project_id, api=api)
        if list_name == 'latest':
            nodes_list = project.nodes_latest
        elif list_name == 'blog':
            nodes_list = project.nodes_blog
        else:
            nodes_list = project.nodes_featured

        if not nodes_list:
            node_list_name = 'nodes_' + list_name
            project[node_list_name] = []
            nodes_list = project[node_list_name]
        elif len(nodes_list) > 5:
            nodes_list.pop(0)

        if node._id in nodes_list:
            # Pop to put this back on top of the list
            nodes_list.remove(node._id)
            if list_name == 'featured':
                # We treat the action as a toggle and do not att the item back
                project.update(api=api)
                return "removed"

        nodes_list.append(node._id)
        project.update(api=api)
        return "added"


@blueprint.route('/create')
@login_required
def create():
    """Create a new project. This is a multi step operation that involves:
    - initialize basic node types
    - initialize basic permissions
    - create and connect storage space
    """
    api = system_util.pillar_api()
    project_properties = dict(
        name='My project',
        user=current_user.objectid,
        category='assets',
        status='pending'
    )
    project = Project(project_properties)
    project.create(api=api)

    return redirect(url_for('projects.edit',
                            project_url="p-{}".format(project['_id'])))


@blueprint.route('/delete', methods=['POST'])
@login_required
def delete():
    """Unapologetically deletes a project"""
    api = system_util.pillar_api()
    project_id = request.form['project_id']
    project = Project.find(project_id, api=api)
    project.delete(api=api)
    return jsonify(dict(staus='success', data=dict(
        message='Project deleted {}'.format(project['_id']))))
