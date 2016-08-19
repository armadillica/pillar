from pillarsdk import Node
from pillarsdk import Project
from pillarsdk.exceptions import ResourceNotFound
from flask import abort
from flask import render_template
from flask import redirect
from flask.ext.login import login_required
from flask.ext.login import current_user
from pillar.web.utils import system_util
from pillar.web.utils import attach_project_pictures
from pillar.web.utils import get_file

from pillar.web.nodes.routes import blueprint
from pillar.web.nodes.routes import url_for_node
from pillar.web.nodes.forms import get_node_form
from pillar.web.nodes.forms import process_node_form
from pillar.web.projects.routes import project_update_nodes_list


def posts_view(project_id, url=None):
    """View individual blogpost"""
    api = system_util.pillar_api()
    # Fetch project (for backgroud images and links generation)
    project = Project.find(project_id, api=api)
    attach_project_pictures(project, api)
    try:
        blog = Node.find_one({
            'where': {'node_type': 'blog', 'project': project_id},
            }, api=api)
    except ResourceNotFound:
        abort(404)
    if url:
        try:
            post = Node.find_one({
                'where': '{"parent": "%s", "properties.url": "%s"}' % (blog._id, url),
                'embedded': '{"node_type": 1, "user": 1}',
                }, api=api)
            if post.picture:
                post.picture = get_file(post.picture, api=api)
        except ResourceNotFound:
            return abort(404)

        # If post is not published, check that the user is also the author of
        # the post. If not, return 404.
        if post.properties.status != "published":
            if current_user.is_authenticated:
                if not post.has_method('PUT'):
                    abort(403)
            else:
                abort(403)

        return render_template(
            'nodes/custom/post/view.html',
            blog=blog,
            node=post,
            project=project,
            title='blog',
            api=api)
    else:
        node_type_post = project.get_node_type('post')
        status_query = "" if blog.has_method('PUT') else ', "properties.status": "published"'
        posts = Node.all({
            'where': '{"parent": "%s" %s}' % (blog._id, status_query),
            'embedded': '{"user": 1}',
            'sort': '-_created'
            }, api=api)

        for post in posts._items:
            post.picture = get_file(post.picture, api=api)

        return render_template(
            'nodes/custom/blog/index.html',
            node_type_post=node_type_post,
            posts=posts._items,
            project=project,
            title='blog',
            api=api)


@blueprint.route("/posts/<project_id>/create", methods=['GET', 'POST'])
@login_required
def posts_create(project_id):
    api = system_util.pillar_api()
    try:
        project = Project.find(project_id, api=api)
    except ResourceNotFound:
        return abort(404)
    attach_project_pictures(project, api)

    blog = Node.find_one({
        'where': {'node_type': 'blog', 'project': project_id}}, api=api)
    node_type = project.get_node_type('post')
    # Check if user is allowed to create a post in the blog
    if not project.node_type_has_method('post', 'POST', api=api):
        return abort(403)
    form = get_node_form(node_type)
    if form.validate_on_submit():
        # Create new post object from scratch
        post_props = dict(
            node_type='post',
            name=form.name.data,
            picture=form.picture.data,
            user=current_user.objectid,
            parent=blog._id,
            project=project._id,
            properties=dict(
                content=form.content.data,
                status=form.status.data,
                url=form.url.data))
        if form.picture.data == '':
            post_props['picture'] = None
        post = Node(post_props)
        post.create(api=api)
        # Only if the node is set as published, push it to the list
        if post.properties.status == 'published':
            project_update_nodes_list(post, project_id=project._id, list_name='blog')
        return redirect(url_for_node(node=post))
    form.parent.data = blog._id
    return render_template('nodes/custom/post/create.html',
        node_type=node_type,
        form=form,
        project=project,
        api=api)


@blueprint.route("/posts/<post_id>/edit", methods=['GET', 'POST'])
@login_required
def posts_edit(post_id):
    api = system_util.pillar_api()

    try:
        post = Node.find(post_id, {
            'embedded': '{"user": 1}'}, api=api)
    except ResourceNotFound:
        return abort(404)
    # Check if user is allowed to edit the post
    if not post.has_method('PUT'):
        return abort(403)

    project = Project.find(post.project, api=api)
    attach_project_pictures(project, api)

    node_type = project.get_node_type(post.node_type)
    form = get_node_form(node_type)
    if form.validate_on_submit():
        if process_node_form(form, node_id=post_id, node_type=node_type,
                             user=current_user.objectid):
            # The the post is published, add it to the list
            if form.status.data == 'published':
                project_update_nodes_list(post, project_id=project._id, list_name='blog')
            return redirect(url_for_node(node=post))
    form.parent.data = post.parent
    form.name.data = post.name
    form.content.data = post.properties.content
    form.status.data = post.properties.status
    form.url.data = post.properties.url
    if post.picture:
        form.picture.data = post.picture
        # Embed picture file
        post.picture = get_file(post.picture, api=api)
    if post.properties.picture_square:
        form.picture_square.data = post.properties.picture_square
    return render_template('nodes/custom/post/edit.html',
                           node_type=node_type,
                           post=post,
                           form=form,
                           project=project,
                           api=api)
