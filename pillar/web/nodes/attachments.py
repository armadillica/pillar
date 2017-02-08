import logging
import re

from bson import ObjectId
import flask
import pillarsdk
import wtforms

from pillar.api.node_types import ATTACHMENT_SLUG_REGEX
from pillar.web.utils import system_util
from pillar.web.utils.forms import build_file_select_form, CustomFormField

shortcode_re = re.compile(r'@\[(%s)\]' % ATTACHMENT_SLUG_REGEX)
log = logging.getLogger(__name__)


def render_attachments(node, field_value):
    """Renders attachments referenced in the field value.

    Returns the rendered field.
    """

    # TODO: cache this based on the node's etag and attachment links expiry.

    node_attachments = node.properties.attachments or {}
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

    return renderer(attachment)


def render_attachment_file(attachment):
    """Renders a file attachment."""

    api = system_util.pillar_api()
    sdk_file = pillarsdk.File.find(attachment[u'oid'], api=api)

    file_renderers = {
        'image': render_attachment_file_image
    }

    mime_type_cat, _ = sdk_file.content_type.split('/', 1)
    try:
        renderer = file_renderers[mime_type_cat]
    except KeyError:
        return flask.render_template('nodes/attachments/file_generic.html', file=sdk_file)

    return renderer(sdk_file, attachment)


def render_attachment_file_image(sdk_file, attachment):
    """Renders an image file."""

    variations = {var.size: var for var in sdk_file.variations}
    return flask.render_template('nodes/attachments/file_image.html',
                                 file=sdk_file, vars=variations, attachment=attachment)


def attachment_form_group_create(schema_prop):
    """Creates a wtforms.FieldList for attachments."""

    file_select_form_group = _attachment_build_single_field(schema_prop)
    field = wtforms.FieldList(CustomFormField(file_select_form_group), min_entries=1)

    return field


def _attachment_build_single_field(schema_prop):
    # Ugly hard-coded schema.
    fake_schema = {
        'slug': schema_prop['propertyschema'],
        'oid': schema_prop['valueschema']['schema']['oid'],
        'link': schema_prop['valueschema']['schema']['link'],
        'link_custom': schema_prop['valueschema']['schema']['link_custom'],
    }
    file_select_form_group = build_file_select_form(fake_schema)
    return file_select_form_group


def attachment_form_group_set_data(db_prop_value, schema_prop, field_list):
    """Populates the attachment form group with data from MongoDB."""

    assert isinstance(db_prop_value, dict)

    # Extra entries are caused by min_entries=1 in the form creation.
    while len(field_list):
        field_list.pop_entry()

    for slug, att_data in sorted(db_prop_value.iteritems()):
        file_select_form_group = _attachment_build_single_field(schema_prop)
        subform = file_select_form_group()

        # Even uglier hard-coded
        subform.slug = slug
        subform.oid = att_data['oid']
        subform.link = 'self'
        subform.link_custom = None
        if 'link' in att_data:
            subform.link = att_data['link']
        if 'link_custom' in att_data:
            subform.link_custom = att_data['link_custom']
        field_list.append_entry(subform)


def attachment_form_parse_post_data(data):
    """Returns a dict that can be stored in the node.properties.attachments."""

    attachments = {}

    # 'allprops' contains all properties, including the slug (which should be a key).
    for allprops in data:
        oid = allprops['oid']
        slug = allprops['slug']
        link = allprops['link']
        link_custom = allprops['link_custom']

        if not allprops['slug'] and not oid:
            continue

        if slug in attachments:
            raise ValueError('Slug "%s" is used more than once' % slug)
        attachments[slug] = {'oid': oid}
        attachments[slug]['link'] = link

        if link == 'custom':
            attachments[slug]['link_custom'] = link_custom

    return attachments
