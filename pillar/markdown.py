"""Bleached Markdown functionality.

This is for user-generated stuff, like comments.
"""

import bleach
import CommonMark

from . import shortcodes

ALLOWED_TAGS = [
    'a',
    'abbr',
    'acronym',
    'b', 'strong',
    'i', 'em',
    'del', 'kbd',
    'dl', 'dt', 'dd',
    'blockquote',
    'code', 'pre',
    'li', 'ol', 'ul',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'p', 'br', 'hr',
    'sup', 'sub', 'strike',
    'img',
    'iframe',
    'video',
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target'],
    'abbr': ['title'],
    'acronym': ['title'],
    'img': ['src', 'alt', 'width', 'height', 'title'],
    'iframe': ['src', 'width', 'height', 'frameborder', 'allowfullscreen'],
    'video': ['autoplay', 'controls', 'loop', 'muted', 'src'],
    '*': ['style'],
}

ALLOWED_STYLES = [
    'color', 'font-weight', 'background-color',
]


def markdown(s: str) -> str:
    commented_shortcodes = shortcodes.comment_shortcodes(s)
    tainted_html = CommonMark.commonmark(commented_shortcodes)

    # Create a Cleaner that supports parsing of bare links (see filters).
    cleaner = bleach.Cleaner(tags=ALLOWED_TAGS,
                             attributes=ALLOWED_ATTRIBUTES,
                             styles=ALLOWED_STYLES,
                             strip_comments=False,
                             filters=[bleach.linkifier.LinkifyFilter])

    safe_html = cleaner.clean(tainted_html)
    return safe_html


def cache_field_name(field_name: str) -> str:
    """Return the field name containing the cached HTML.

    See ValidateCustomFields._normalize_coerce_markdown().
    """
    return f'_{field_name}_html'
