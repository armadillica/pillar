"""Our custom Jinja filters and other template stuff."""

import functools
import json
import logging
import typing
import urllib.parse

import flask
import flask_login
import jinja2.filters
import jinja2.utils
import werkzeug.exceptions as wz_exceptions
import pillarsdk

import pillar.api.utils
from pillar import auth
from pillar.api.utils import pretty_duration
from pillar.web.utils import pretty_date
from pillar.web.nodes.routes import url_for_node
import pillar.markdown

log = logging.getLogger(__name__)


def format_pretty_date(d):
    return pretty_date(d)


def format_pretty_date_time(d):
    return pretty_date(d, detail=True)


def format_pretty_duration(s):
    return pretty_duration(s)


def format_undertitle(s):
    """Underscore-replacing title filter.

    Replaces underscores with spaces, and then applies Jinja2's own title filter.
    """

    # Just keep empty strings and Nones as they are.
    if not s:
        return s

    return jinja2.filters.do_title(s.replace('_', ' '))


def do_hide_none(s):
    """Returns the input, or an empty string if the input is None."""

    if s is None:
        return ''
    return s


# Source: Django, django/template/defaultfilters.py
def do_pluralize(value, arg='s'):
    """
    Returns a plural suffix if the value is not 1. By default, 's' is used as
    the suffix:

    * If value is 0, vote{{ value|pluralize }} displays "0 votes".
    * If value is 1, vote{{ value|pluralize }} displays "1 vote".
    * If value is 2, vote{{ value|pluralize }} displays "2 votes".

    If an argument is provided, that string is used instead:

    * If value is 0, class{{ value|pluralize:"es" }} displays "0 classes".
    * If value is 1, class{{ value|pluralize:"es" }} displays "1 class".
    * If value is 2, class{{ value|pluralize:"es" }} displays "2 classes".

    If the provided argument contains a comma, the text before the comma is
    used for the singular case and the text after the comma is used for the
    plural case:

    * If value is 0, cand{{ value|pluralize:"y,ies" }} displays "0 candies".
    * If value is 1, cand{{ value|pluralize:"y,ies" }} displays "1 candy".
    * If value is 2, cand{{ value|pluralize:"y,ies" }} displays "2 candies".
    """

    if ',' not in arg:
        arg = ',' + arg
    bits = arg.split(',')
    if len(bits) > 2:
        return ''
    singular_suffix, plural_suffix = bits[:2]

    try:
        if float(value) != 1:
            return plural_suffix
    except ValueError:  # Invalid string that's not a number.
        pass
    except TypeError:  # Value isn't a string or a number; maybe it's a list?
        try:
            if len(value) != 1:
                return plural_suffix
        except TypeError:  # len() of unsized object.
            pass
    return singular_suffix


def do_markdown(s: typing.Optional[str]):
    """Convert Markdown.

    This filter is not preferred. Use {'coerce': 'markdown'} in the Eve schema
    instead, to cache the HTML in the database, and use do_markdowned() to
    fetch it.

    Jinja example: {{ node.properties.content | markdown }}
    """
    if s is None:
        return None

    if not s:
        return s

    # FIXME: get rid of this filter altogether and cache HTML of comments.
    safe_html = pillar.markdown.markdown(s)
    return jinja2.utils.Markup(safe_html)


def _get_markdowned_html(document: typing.Union[dict, pillarsdk.Resource], field_name: str) -> str:
    """Fetch pre-converted Markdown or render on the fly.

    Use {'coerce': 'markdown'} in the Eve schema to cache the HTML in the
    database and use do_markdowned() to fetch it in a safe way.

    Places shortcode tags `{...}` between HTML comments, so that they pass
    through the Markdown parser as-is.
    """
    if isinstance(document, pillarsdk.Resource):
        document = document.to_dict()
    if not document:
        # If it's empty, we don't care what it is.
        return ''
    assert isinstance(document, dict), \
        f'document should be dict or pillarsdk.Resource, not {document!r}'

    cache_field_name = pillar.markdown.cache_field_name(field_name)
    html = document.get(cache_field_name)
    if html is None:
        markdown_src = document.get(field_name) or ''
        html = pillar.markdown.markdown(markdown_src)
    return html


def do_markdowned(document: typing.Union[dict, pillarsdk.Resource], field_name: str) \
        -> jinja2.utils.Markup:
    """Render Markdown and shortcodes.

    Use {'coerce': 'markdown'} in the Eve schema to cache the HTML in the
    database and use do_markdowned() to fetch it in a safe way.

    Jinja example: {{ node.properties | markdowned('content') }}

    The value of `document` is sent as context to the shortcodes render
    function.
    """
    from pillar import shortcodes
    html = _get_markdowned_html(document, field_name)
    html = shortcodes.render_commented(html, context=document)
    return jinja2.utils.Markup(html)


def do_url_for_node(node_id=None, node=None):
    try:
        return url_for_node(node_id=node_id, node=node)
    except wz_exceptions.NotFound:
        log.info('%s: do_url_for_node(node_id=%r, ...) called for non-existing node.',
                 flask.request.url, node_id)
        return None


# Source: Django 1.9 defaultfilters.py
def do_yesno(value, arg=None):
    """
    Given a string mapping values for true, false and (optionally) None,
    returns one of those strings according to the value:

    ==========  ======================  ==================================
    Value       Argument                Outputs
    ==========  ======================  ==================================
    ``True``    ``"yeah,no,maybe"``     ``yeah``
    ``False``   ``"yeah,no,maybe"``     ``no``
    ``None``    ``"yeah,no,maybe"``     ``maybe``
    ``None``    ``"yeah,no"``           ``"no"`` (converts None to False
                                        if no mapping for None is given.
    ==========  ======================  ==================================
    """
    if arg is None:
        arg = 'yes,no,maybe'
    bits = arg.split(',')
    if len(bits) < 2:
        return value  # Invalid arg.
    try:
        yes, no, maybe = bits
    except ValueError:
        # Unpack list of wrong size (no "maybe" value provided).
        yes, no, maybe = bits[0], bits[1], bits[1]
    if value is None:
        return maybe
    if value:
        return yes
    return no


def user_to_dict(user: auth.UserClass) -> dict:
    return dict(
        user_id=str(user.user_id),
        username=user.username,
        full_name=user.full_name,
        gravatar=user.gravatar,
        email=user.email,
        capabilities=list(user.capabilities),
        badges_html=user.badges_html,
        is_authenticated=user.is_authenticated
    )


def do_json(some_object) -> str:
    if isinstance(some_object, pillarsdk.Resource):
        some_object = some_object.to_dict()
    if isinstance(some_object, auth.UserClass):
        some_object = user_to_dict(some_object)
    return json.dumps(some_object)


def setup_jinja_env(jinja_env, app_config: dict):
    jinja_env.filters['pretty_date'] = format_pretty_date
    jinja_env.filters['pretty_date_time'] = format_pretty_date_time
    jinja_env.filters['pretty_duration'] = format_pretty_duration
    jinja_env.filters['undertitle'] = format_undertitle
    jinja_env.filters['hide_none'] = do_hide_none
    jinja_env.filters['pluralize'] = do_pluralize
    jinja_env.filters['gravatar'] = pillar.api.utils.gravatar
    jinja_env.filters['markdown'] = do_markdown
    jinja_env.filters['markdowned'] = do_markdowned
    jinja_env.filters['yesno'] = do_yesno
    jinja_env.filters['repr'] = repr
    jinja_env.filters['urljoin'] = functools.partial(urllib.parse.urljoin, allow_fragments=True)
    jinja_env.filters['json'] = do_json
    jinja_env.globals['url_for_node'] = do_url_for_node
    jinja_env.globals['abs_url'] = functools.partial(flask.url_for,
                                                     _external=True,
                                                     _scheme=app_config['SCHEME'])
    jinja_env.globals['session'] = flask.session
    jinja_env.globals['current_user'] = flask_login.current_user
