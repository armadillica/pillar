"""Attachment form handling."""

import logging

import wtforms

from pillar.web.utils.forms import build_file_select_form, CustomFormField

log = logging.getLogger(__name__)


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
    }
    file_select_form_group = build_file_select_form(fake_schema)
    return file_select_form_group


def attachment_form_group_set_data(db_prop_value, schema_prop, field_list):
    """Populates the attachment form group with data from MongoDB."""

    assert isinstance(db_prop_value, dict)

    # Extra entries are caused by min_entries=1 in the form creation.
    while len(field_list):
        field_list.pop_entry()

    for slug, att_data in sorted(db_prop_value.items()):
        file_select_form_group = _attachment_build_single_field(schema_prop)
        subform = file_select_form_group()

        # Even uglier hard-coded
        subform.slug = slug
        subform.oid = att_data['oid']
        field_list.append_entry(subform)


def attachment_form_parse_post_data(data) -> dict:
    """Returns a dict that can be stored in the node.properties.attachments."""

    attachments = {}

    # 'allprops' contains all properties, including the slug (which should be a key).
    for allprops in data:
        oid = allprops['oid']
        slug = allprops['slug']

        if not allprops['slug'] or not oid:
            continue

        if slug in attachments:
            raise ValueError('Slug "%s" is used more than once' % slug)
        attachments[slug] = {'oid': oid}

    return attachments
