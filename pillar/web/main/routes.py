import logging
import urllib.parse
import warnings

from pillarsdk import Node
from flask import Blueprint
from flask import current_app
from flask import render_template
from flask import redirect
from flask import request

from pillar.flask_extra import ensure_schema
from pillar.web.utils import system_util
from pillar.web.nodes.routes import url_for_node
from pillar.web.nodes.custom.posts import posts_view
from pillar.web.nodes.custom.posts import posts_create

blueprint = Blueprint('main', __name__)
log = logging.getLogger(__name__)


@blueprint.route('/')
def homepage():
    return render_template('homepage.html')


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


@blueprint.route('/blog-archive/')
@blueprint.route('/blog-archive/<int:page>')
def main_blog_archive(page=1):
    project_id = current_app.config['MAIN_PROJECT_ID']
    return posts_view(project_id, archive=True, page=page)


@blueprint.route('/p/<project_url>/blog-archive/')
@blueprint.route('/p/<project_url>/blog-archive/<int:page>')
def project_blog_archive(project_url, page=1):
    return posts_view(project_url=project_url, archive=True, page=page)


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


@blueprint.route('/feeds/blogs.atom')
def feeds_blogs():
    """Global feed generator for latest blogposts across all projects"""

    # Werkzeug deprecated their Atom feed. Tracked in https://developer.blender.org/T65274.
    with warnings.catch_warnings():
        from werkzeug.contrib.atom import AtomFeed

    @current_app.cache.cached(60*5)
    def render_page():
        feed = AtomFeed('Blender Cloud - Latest updates',
                        feed_url=ensure_schema(request.url),
                        url=ensure_schema(request.url_root))
        # Get latest blog posts
        api = system_util.pillar_api()
        latest_posts = Node.all({
            'where': {'node_type': 'post', 'properties.status': 'published'},
            'embedded': {'user': 1},
            'sort': '-_created',
            'max_results': '15'
            }, api=api)

        newest = None

        # Populate the feed
        for post in latest_posts._items:
            author = post.user.fullname or post.user.username
            updated = post._updated if post._updated else post._created
            url = ensure_schema(urllib.parse.urljoin(request.host_url, url_for_node(node=post)))
            content = post.properties.content[:500]
            content = '<p>{0}... <a href="{1}">Read more</a></p>'.format(content, url)

            if newest is None:
                newest = updated
            else:
                newest = max(newest, updated)

            feed.add(post.name, str(content),
                     content_type='html',
                     author=author,
                     url=url,
                     updated=updated,
                     published=post._created)
        resp = feed.get_response()
        if newest is not None:
            resp.headers['Last-Modified'] = newest.strftime(current_app.config['RFC1123_DATE_FORMAT'])
        return resp
    return render_page()


@blueprint.route('/search')
def nodes_search_index():
    return render_template('nodes/search.html')
