import itertools
import logging

from pillarsdk import Node
from pillarsdk import Project
from pillarsdk.exceptions import ResourceNotFound
from flask import abort
from flask import Blueprint
from flask import current_app
from flask import render_template
from flask import redirect
from flask import request
from flask_login import current_user
from werkzeug.contrib.atom import AtomFeed

from pillar.web.utils import system_util
from pillar.web.nodes.routes import url_for_node
from pillar.web.nodes.custom.posts import posts_view
from pillar.web.nodes.custom.posts import posts_create
from pillar.web.utils import attach_project_pictures
from pillar.web.utils import current_user_is_authenticated
from pillar.web.utils import get_file

blueprint = Blueprint('main', __name__)
log = logging.getLogger(__name__)


@blueprint.route('/')
def homepage():
    # Workaround to cache rendering of a page if user not logged in
    @current_app.cache.cached(timeout=3600)
    def render_page():
        return render_template('join.html')

    if current_user.is_anonymous:
        return render_page()

    # Get latest blog posts
    api = system_util.pillar_api()
    latest_posts = Node.all({
        'projection': {'name': 1, 'project': 1, 'node_type': 1,
                       'picture': 1, 'properties.status': 1, 'properties.url': 1},
        'where': {'node_type': 'post', 'properties.status': 'published'},
        'embedded': {'project': 1},
        'sort': '-_created',
        'max_results': '5'
        }, api=api)

    # Append picture Files to last_posts
    for post in latest_posts._items:
        post.picture = get_file(post.picture, api=api)

    # Get latest assets added to any project
    latest_assets = Node.latest('assets', api=api)

    # Append picture Files to latest_assets
    for asset in latest_assets._items:
        asset.picture = get_file(asset.picture, api=api)

    # Get latest comments to any node
    latest_comments = Node.latest('comments', api=api)

    # Get a list of random featured assets
    random_featured = get_random_featured_nodes()

    # Parse results for replies
    to_remove = []
    for idx, comment in enumerate(latest_comments._items):
        if comment.properties.is_reply:
            try:
                comment.attached_to = Node.find(comment.parent.parent,
                                                {'projection': {
                                                    '_id': 1,
                                                    'name': 1,
                                                }},
                                                api=api)
            except ResourceNotFound:
                # Remove this comment
                to_remove.append(idx)
        else:
            comment.attached_to = comment.parent

    for idx in reversed(to_remove):
        del latest_comments._items[idx]

    main_project = Project.find(current_app.config['MAIN_PROJECT_ID'], api=api)
    main_project.picture_header = get_file(main_project.picture_header, api=api)

    # Merge latest assets and comments into one activity stream.
    def sort_key(item):
        return item._created

    activities = itertools.chain(latest_assets._items,
                                 latest_comments._items)
    activity_stream = sorted(activities, key=sort_key, reverse=True)

    return render_template(
        'homepage.html',
        main_project=main_project,
        latest_posts=latest_posts._items,
        activity_stream=activity_stream,
        random_featured=random_featured,
        api=api)


# @blueprint.errorhandler(500)
# def error_500(e):
#     return render_template('errors/500.html'), 500
#
#
# @blueprint.errorhandler(404)
# def error_404(e):
#     return render_template('errors/404.html'), 404
#
#
# @blueprint.errorhandler(403)
# def error_404(e):
#     return render_template('errors/403_embed.html'), 403
#

@blueprint.route('/join')
def join():
    """Join page"""
    return redirect('https://store.blender.org/product/membership/')


@blueprint.route('/services')
def services():
    """Services page"""
    return render_template('services.html')


@blueprint.route('/blog/')
@blueprint.route('/blog/<url>')
def main_blog(url=None):
    """Blog with project news"""
    project_id = current_app.config['MAIN_PROJECT_ID']
    return posts_view(project_id, url=url)


@blueprint.route('/blog/create')
def main_posts_create():
    project_id = current_app.config['MAIN_PROJECT_ID']
    return posts_create(project_id)


@blueprint.route('/p/<project_url>/blog/')
@blueprint.route('/p/<project_url>/blog/<url>')
def project_blog(project_url, url=None):
    """View project blog"""
    return posts_view(project_url=project_url, url=url)


def get_projects(category):
    """Utility to get projects based on category. Should be moved on the API
    and improved with more extensive filtering capabilities.
    """
    api = system_util.pillar_api()
    projects = Project.all({
        'where': {
            'category': category,
            'is_private': False},
        'sort': '-_created',
        }, api=api)
    for project in projects._items:
        attach_project_pictures(project, api)
    return projects


def get_random_featured_nodes():

    import random

    api = system_util.pillar_api()
    projects = Project.all({
        'projection': {'nodes_featured': 1},
        'where': {'is_private': False},
        'max_results': '15'
        }, api=api)

    featured_nodes = (p.nodes_featured for p in projects._items if p.nodes_featured)
    featured_nodes = [item for sublist in featured_nodes for item in sublist]
    if len(featured_nodes) > 3:
        featured_nodes = random.sample(featured_nodes, 3)

    featured_node_documents = []

    for node in featured_nodes:
        node_document = Node.find(node, {
                'projection': {'name': 1, 'project': 1, 'picture': 1,
                                'properties.content_type': 1, 'properties.url': 1},
                'embedded': {'project': 1}
            }, api=api)

        node_document.picture = get_file(node_document.picture, api=api)
        featured_node_documents.append(node_document)

    return featured_node_documents


@blueprint.route('/open-projects')
def open_projects():
    @current_app.cache.cached(timeout=3600, unless=current_user_is_authenticated)
    def render_page():
        projects = get_projects('film')
        return render_template(
            'projects/index_collection.html',
            title='open-projects',
            projects=projects._items,
            api=system_util.pillar_api())

    return render_page()


@blueprint.route('/training')
def training():
    @current_app.cache.cached(timeout=3600, unless=current_user_is_authenticated)
    def render_page():
        projects = get_projects('training')
        return render_template(
            'projects/index_collection.html',
            title='training',
            projects=projects._items,
            api=system_util.pillar_api())

    return render_page()


@blueprint.route('/gallery')
def gallery():
    return redirect('/p/gallery')


@blueprint.route('/textures')
def redir_textures():
    return redirect('/p/textures')


@blueprint.route('/hdri')
def redir_hdri():
    return redirect('/p/hdri')


@blueprint.route('/caminandes')
def caminandes():
    return redirect('/p/caminandes-3')


@blueprint.route('/cf2')
def cf2():
    return redirect('/p/creature-factory-2')


@blueprint.route('/characters')
def redir_characters():
    return redirect('/p/characters')


@blueprint.route('/vrview')
def vrview():
    """Call this from iframes to render sperical content (video and images)"""
    if 'image' not in request.args:
        return redirect('/')
    return render_template('vrview.html')


@blueprint.route('/403')
def error_403():
    """Custom entry point to display the not allowed template"""
    return render_template('errors/403_embed.html')


@blueprint.route('/join-agent')
def join_agent():
    """Custom page to support Agent 327 barbershop campaign"""
    return render_template('join_agent.html')


# Shameful redirects
@blueprint.route('/p/blender-cloud/')
def redirect_cloud_blog():
    return redirect('/blog')


@blueprint.route('/feeds/blogs.atom')
def feeds_blogs():
    """Global feed generator for latest blogposts across all projects"""
    @current_app.cache.cached(60*5)
    def render_page():
        feed = AtomFeed('Blender Cloud - Latest updates',
                        feed_url=request.url, url=request.url_root)
        # Get latest blog posts
        api = system_util.pillar_api()
        latest_posts = Node.all({
            'where': {'node_type': 'post', 'properties.status': 'published'},
            'embedded': {'user': 1},
            'sort': '-_created',
            'max_results': '15'
            }, api=api)

        # Populate the feed
        for post in latest_posts._items:
            author = post.user.fullname
            updated = post._updated if post._updated else post._created
            url = url_for_node(node=post)
            content = post.properties.content[:500]
            content = u'<p>{0}... <a href="{1}">Read more</a></p>'.format(content, url)
            feed.add(post.name, unicode(content),
                     content_type='html',
                     author=author,
                     url=url,
                     updated=updated,
                     published=post._created)
        return feed.get_response()
    return render_page()


@blueprint.route('/search')
def nodes_search_index():
    return render_template('nodes/search.html')
