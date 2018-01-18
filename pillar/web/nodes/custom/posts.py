import functools
import logging

from pillarsdk import Node
from pillarsdk import Project
from pillarsdk.exceptions import ResourceNotFound
from flask import abort, url_for
from flask import current_app
from flask import render_template
from flask import redirect
from flask_login import login_required, current_user
from pillar.web.utils import system_util
from pillar.web.utils import attach_project_pictures
from pillar.web.utils import get_file
from pillar.web.utils import current_user_is_authenticated

from pillar.web.nodes.routes import blueprint
from pillar.web.nodes.routes import url_for_node
from pillar.web.nodes.forms import get_node_form
import pillar.web.nodes.attachments
from pillar.web.projects.routes import project_update_nodes_list

log = logging.getLogger(__name__)


# Cached, see setup_app() below.
def posts_view(project_id=None, project_url=None, url=None, *, archive=False, page=1):
    """View individual blogpost"""

    if bool(project_id) == bool(project_url):
        raise ValueError('posts_view(): pass either project_id or project_url')

    if url and archive:
        raise ValueError('posts_view(): cannot pass both url and archive')

    api = system_util.pillar_api()

    # Fetch project (for background images and links generation)
    if project_id:
        project = Project.find(project_id, api=api)
    else:
        project = Project.find_one({'where': {'url': project_url}}, api=api)
        project_id = project['_id']

    attach_project_pictures(project, api)

    blog = Node.find_one({
        'where': {'node_type': 'blog', 'project': project_id},
    }, api=api)

    status_query = {} if blog.has_method('PUT') else {'properties.status': 'published'}
    posts = Node.all({
        'where': {'parent': blog._id, **status_query},
        'embedded': {'user': 1},
        'sort': '-_created',
        'max_results': 20 if archive else 5,
        'page': page,
    }, api=api)

    for post in posts._items:
        post.picture = get_file(post.picture, api=api)
        post.url = url_for_node(node=post)

    # Use the *_main_project.html template for the main blog
    is_main_project = project_id == current_app.config['MAIN_PROJECT_ID']
    main_project_template = '_main_project' if is_main_project else ''
    index_arch = 'archive' if archive else 'index'
    template_path = f'nodes/custom/blog/{index_arch}{main_project_template}.html',

    if url:
        template_path = f'nodes/custom/post/view{main_project_template}.html',

        post = Node.find_one({
            'where': {'parent': blog._id, 'properties.url': url},
            'embedded': {'node_type': 1, 'user': 1},
        }, api=api)

        if post.picture:
            post.picture = get_file(post.picture, api=api)

        post.url = url_for_node(node=post)
    elif posts._items:
        post = posts._items[0]
    else:
        post = None

    if post is not None:
        # If post is not published, check that the user is also the author of
        # the post. If not, return 404.
        if post.properties.status != "published":
            if not (current_user.is_authenticated and post.has_method('PUT')):
                abort(403)

        try:
            post_contents = post['properties']['content']
        except KeyError:
            log.warning('Blog post %s has no content', post._id)
        else:
            post['properties']['content'] = pillar.web.nodes.attachments.render_attachments(
                post, post_contents)

    can_create_blog_posts = project.node_type_has_method('post', 'POST', api=api)

    # Use functools.partial so we can later pass page=X.
    if is_main_project:
        url_func = functools.partial(url_for, 'main.main_blog_archive')
    else:
        url_func = functools.partial(url_for, 'main.project_blog_archive', project_url=project.url)

    project.blog_archive_url = url_func()
    pmeta = posts._meta
    seen_now = pmeta['max_results'] * pmeta['page']
    if pmeta['total'] > seen_now:
        project.blog_archive_next = url_func(page=pmeta['page'] + 1)
    else:
        project.blog_archive_next = None
    if pmeta['page'] > 1:
        project.blog_archive_prev = url_func(page=pmeta['page'] - 1)
    else:
        project.blog_archive_prev = None

    return render_template(
        template_path,
        blog=blog,
        node=post,
        posts=posts._items,
        posts_meta=pmeta,
        more_posts_available=pmeta['total'] > pmeta['max_results'],
        project=project,
        title='blog',
        node_type_post=project.get_node_type('post'),
        can_create_blog_posts=can_create_blog_posts,
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


def setup_app(app):
    global posts_view

    memoize = app.cache.memoize(timeout=3600, unless=current_user_is_authenticated)
    posts_view = memoize(posts_view)
