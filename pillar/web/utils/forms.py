import json

from markupsafe import Markup

from pillarsdk import File
from flask import current_app
from flask_login import current_user
from wtforms import Form
from wtforms import StringField
from wtforms import SelectField
from wtforms import BooleanField
from wtforms.compat import text_type
from wtforms.widgets import html_params
from wtforms.widgets import HiddenInput
from wtforms.widgets import HTMLString
from wtforms.fields import FormField
from wtforms import validators
from pillarsdk.exceptions import ResourceNotFound
from pillar.web import system_util


class CustomFileSelectWidget(HiddenInput):
    def __init__(self, file_format=None, **kwargs):
        super(CustomFileSelectWidget, self).__init__(**kwargs)
        self.file_format = file_format

    def __call__(self, field, **kwargs):
        html = super(CustomFileSelectWidget, self).__call__(field, **kwargs)

        file_format = self.file_format
        file_format_regex = ''
        if file_format and file_format == 'image':
            file_format_regex = '^image\/(gif|jpe?g|png|tif?f|tga)$'

        button = [u'<div class="form-upload-file">']

        if field.data:
            api = system_util.pillar_api()
            try:
                # Load the existing file attached to the field
                file_item = File.find(field.data, api=api)
            except ResourceNotFound:
                pass
            else:
                button.append(u'<div class="form-upload-file-meta-container">')

                filename = Markup.escape(file_item.filename)
                if file_item.content_type.split('/')[0] == 'image':
                    # If a file of type image is available, display the preview
                    button.append(u'<img class="preview-thumbnail" src="{0}" />'.format(
                        file_item.thumbnail('s', api=api)))

                button.append(u'<ul class="form-upload-file-meta">')
                # File name
                button.append(u'<li class="name">{0}</li>'.format(filename))
                # File size
                button.append(u'<li class="size">({0} MB)</li>'.format(
                    round((file_item.length / 1024) * 0.001, 2)))
                # Image resolution (if image)
                if file_item.content_type.split('/')[0] == 'image':
                    button.append(u'<li class="dimensions">{0}x{1}</li>'.format(
                        file_item.width, file_item.height))
                button.append(u'</ul>')
                button.append(u'<ul class="form-upload-file-actions">')
                # Download button for original file
                button.append(u'<li class="original">'
                              u'<a href="{}" class="file_original"> '
                              u'<i class="pi-download"></i>Original</a></li>'
                              .format(file_item.link))
                # Delete button
                button.append(u'<li class="delete">'
                              u'<a href="#" class="file_delete" '
                              u'data-field-name="{field_name}" '
                              u'data-file_id="{file_id}"> '
                              u'<i class="pi-trash"></i> Delete</a></li>'.format(
                    field_name=field.name, file_id=field.data))
                button.append(u'</ul>')
                button.append(u'</div>')

        upload_url = u'%sstorage/stream/{project_id}' % current_app.config[
            'PILLAR_SERVER_ENDPOINT']

        button.append(u'<input class="fileupload" type="file" name="file" '
                      u'data-url="{url}" '
                      u'data-field-name="{name}" '
                      u'data-field-slug="{slug}" '
                      u'data-token="{token}" '
                      u'data-file-format="{file_format}">'
                      u'<div class="form-upload-progress"> '
                      u'<div class="form-upload-progress-bar" role="progressbar" '
                      u'aria-valuenow="0" aria-valuemin="0" aria-valuemax="100" '
                      u'style="width: 0%;"> '
                      u'</div> '
                      u'</div>'.format(url=upload_url,
                                       name=field.name,
                                       slug=field.name.replace('oid', 'slug'),
                                       token=Markup.escape(current_user.id),
                                       file_format=Markup.escape(file_format_regex)))

        button.append(u'</div>')

        return HTMLString(html + u''.join(button))


class FileSelectField(StringField):
    def __init__(self, name, file_format=None, **kwargs):
        super(FileSelectField, self).__init__(name, **kwargs)
        self.widget = CustomFileSelectWidget(file_format=file_format)


def build_file_select_form(schema):
    class FileSelectForm(Form):
        pass

    for field_name, field_schema in schema.iteritems():
        if field_schema['type'] == 'boolean':
            field = BooleanField()
        elif field_schema['type'] == 'string':
            if 'allowed' in field_schema:
                choices = [(c, c) for c in field_schema['allowed']]
                field = SelectField(choices=choices)
            else:
                field = StringField()
        elif field_schema['type'] == 'objectid':
            field = FileSelectField('file')
        else:
            raise ValueError('field type %s not supported' % field_schema['type'])

        setattr(FileSelectForm, field_name, field)
    return FileSelectForm


class CustomFormFieldWidget(object):
    """
    Renders a list of fields as in the way we like. Based the TableWidget.

    Hidden fields will not be displayed with a row, instead the field will be
    pushed into a subsequent table row to ensure XHTML validity. Hidden fields
    at the end of the field list will appear outside the table.
    """

    def __call__(self, field, **kwargs):
        html = []
        kwargs.setdefault('id', field.id)
        html.append(u'<div %s>' % html_params(**kwargs))
        hidden = u''
        for subfield in field:
            if subfield.type == 'HiddenField':
                hidden += text_type(subfield)
            else:
                html.append(u'<div><span>%s</span>%s%s</div>' % (
                    text_type(subfield.label), hidden, text_type(subfield)))
                hidden = u''
        html.append(u'</div>')
        if hidden:
            html.append(hidden)
        return HTMLString(u''.join(html))


class CustomFormField(FormField):
    def __init__(self, form_class, **kwargs):
        super(CustomFormField, self).__init__(form_class, **kwargs)
        self.widget = CustomFormFieldWidget()


class JSONRequired(validators.DataRequired):
    """
    Checks the field's data is valid JSON, otherwise stops the validation chain.

    This validator checks that the ``data`` attribute on the field can be parsed
    as JSON string.

    :param message:
        Error message to raise in case of a validation error. If not given,
        uses the message from the ValueError raised by json.loads().
    """

    def __call__(self, form, field):
        super(JSONRequired, self).__call__(form, field)

        try:
            json.loads(field.data)
        except ValueError as ex:
            message = self.message or ex.message

            field.errors[:] = []
            raise validators.StopValidation(message)
