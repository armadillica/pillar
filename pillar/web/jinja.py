"""Our custom Jinja filters and other template stuff."""

from __future__ import absolute_import

import jinja2.filters

from pillar.web.utils import pretty_date
from pillar.web.nodes.routes import url_for_node


def format_pretty_date(d):
    return pretty_date(d)


def format_pretty_date_time(d):
    return pretty_date(d, detail=True)


def format_undertitle(s):
    """Underscore-replacing title filter.

    Replaces underscores with spaces, and then applies Jinja2's own title filter.
    """

    return jinja2.filters.do_title(s.replace('_', ' '))


def do_hide_none(s):
    """Returns the input, or an empty string if the input is None."""

    if s is None:
        return ''
    return s


def setup_jinja_env(jinja_env):
    jinja_env.filters['pretty_date'] = format_pretty_date
    jinja_env.filters['pretty_date_time'] = format_pretty_date_time
    jinja_env.filters['undertitle'] = format_undertitle
    jinja_env.filters['hide_none'] = do_hide_none
    jinja_env.globals['url_for_node'] = url_for_node
