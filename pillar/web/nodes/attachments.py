import logging
import re

from bson import ObjectId
import flask
import pillarsdk

from pillar.api.node_types import ATTACHMENT_SLUG_REGEX
from pillar.web.utils import system_util

shortcode_re = re.compile(r'@\[(%s)\]' % ATTACHMENT_SLUG_REGEX)
log = logging.getLogger(__name__)


def render_attachments(node, field_value):
    """Renders attachments referenced in the field value.

    Returns the rendered field.
    """

    # TODO: cache this based on the node's etag and attachment links expiry.

    node_attachments = node[u'properties'][u'attachments']
    if isinstance(node_attachments, list):
        log.warning('Old-style attachments property found on node %s. Ignoring them, '
                    'will result in attachments not being found.', node[u'_id'])
        return field_value

    if not node_attachments:
        return field_value

    def replace(match):
        slug = match.group(1)

        try:
            att = node_attachments[slug]
        except KeyError:
            return u'[attachment "%s" not found]' % slug

        return render_attachment(att)

    return shortcode_re.sub(replace, field_value)


def render_attachment(attachment):
    """Renders an attachment as HTML"""

    oid = ObjectId(attachment[u'oid'])
    collection = attachment.collection or u'files'

    renderers = {
        'files': render_attachment_file
    }

    try:
        renderer = renderers[collection]
    except KeyError:
        log.error(u'Unable to render attachment from collection %s', collection)
        return u'Unable to render attachment'

    return renderer(oid)


def render_attachment_file(oid):
    """Renders a file attachment."""

    api = system_util.pillar_api()
    sdk_file = pillarsdk.File.find(oid, api=api)

    file_renderers = {
        'image': render_attachment_file_image
    }

    mime_type_cat, _ = sdk_file.content_type.split('/', 1)
    try:
        renderer = file_renderers[mime_type_cat]
    except KeyError:
        return flask.render_template('nodes/attachments/file_generic.html', file=sdk_file)

    return renderer(sdk_file)


def render_attachment_file_image(sdk_file):
    """Renders an image file."""

    variations = {var.size: var for var in sdk_file.variations}
    return flask.render_template('nodes/attachments/file_image.html',
                                 file=sdk_file, vars=variations)
