"""Bleached Markdown functionality.

This is for user-generated stuff, like comments.
"""

import bleach
import CommonMark

ALLOWED_TAGS = [
    'a',
    'abbr',
    'acronym',
    'b', 'strong',
    'i', 'em',
    'del', 'kbd',
    'dl', 'dt', 'dd',
    'blockquote',
    'code',
    'li', 'ol', 'ul',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'p', 'br', 'hr',
    'sup', 'sub', 'strike',
    'img',
    'iframe',
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target'],
    'abbr': ['title'],
    'acronym': ['title'],
    'img': ['src', 'alt', 'width', 'height', 'title'],
    'iframe': ['src', 'width', 'height', 'frameborder', 'allowfullscreen'],
    '*': ['style'],
}

ALLOWED_STYLES = [
    'color', 'font-weight', 'background-color',
]


def markdown(s):
    tainted_html = CommonMark.commonmark(s)
    safe_html = bleach.clean(tainted_html,
                             tags=ALLOWED_TAGS,
                             attributes=ALLOWED_ATTRIBUTES,
                             styles=ALLOWED_STYLES)
    return safe_html
