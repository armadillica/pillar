"""Our custom Jinja filters and other template stuff."""

from __future__ import absolute_import

import jinja2.filters
import jinja2.utils

import pillar.api.utils
from pillar.web.utils import pretty_date
from pillar.web.nodes.routes import url_for_node
import pillar.markdown


def format_pretty_date(d):
    return pretty_date(d)


def format_pretty_date_time(d):
    return pretty_date(d, detail=True)


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


def do_markdown(s):
    # FIXME: get rid of this filter altogether and cache HTML of comments.
    safe_html = pillar.markdown.markdown(s)
    return jinja2.utils.Markup(safe_html)


def setup_jinja_env(jinja_env):
    jinja_env.filters['pretty_date'] = format_pretty_date
    jinja_env.filters['pretty_date_time'] = format_pretty_date_time
    jinja_env.filters['undertitle'] = format_undertitle
    jinja_env.filters['hide_none'] = do_hide_none
    jinja_env.filters['pluralize'] = do_pluralize
    jinja_env.filters['gravatar'] = pillar.api.utils.gravatar
    jinja_env.filters['markdown'] = do_markdown
    jinja_env.globals['url_for_node'] = url_for_node
