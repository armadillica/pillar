import logging

from datetime import datetime
from datetime import date
import pillarsdk
from flask import current_app
from flask_wtf import Form
from wtforms import StringField
from wtforms import DateField
from wtforms import SelectField
from wtforms import HiddenField
from wtforms import BooleanField
from wtforms import IntegerField
from wtforms import FloatField
from wtforms import TextAreaField
from wtforms import DateTimeField
from wtforms import SelectMultipleField
from wtforms import FieldList
from wtforms.validators import DataRequired
from pillar.web.utils import system_util
from pillar.web.utils.forms import FileSelectField
from pillar.web.utils.forms import ProceduralFileSelectForm
from pillar.web.utils.forms import CustomFormField
from pillar.web.utils.forms import build_file_select_form

log = logging.getLogger(__name__)


def add_form_properties(form_class, node_schema, form_schema, prefix=''):
    """Add fields to a form based on the node and form schema provided.
    :type node_schema: dict
    :param node_schema: the validation schema used by Cerberus
    :type form_class: class
    :param form_class: The form class to which we append fields
    :type form_schema: dict
    :param form_schema: description of how to build the form (which fields to
            show and hide)
    """

    for prop, schema_prop in node_schema.iteritems():
        form_prop = form_schema.get(prop, {})
        if prop == 'items':
            continue
        if not form_prop.get('visible', True):
            continue
        prop_name = "{0}{1}".format(prefix, prop)

        # Recursive call if detects a dict
        field_type = schema_prop['type']
        if field_type == 'dict':
            # This works if the dictionary schema is hardcoded.
            # If we define it using propertyschema and valueschema, this
            # validation pattern does not work and crahses.
            add_form_properties(form_class, schema_prop['schema'],
                                form_prop['schema'], "{0}__".format(prop_name))
            continue

        if field_type == 'list':
            if prop == 'attachments':
                # class AttachmentForm(Form):
                #     pass
                # AttachmentForm.file = FileSelectField('file')
                # AttachmentForm.size = StringField()
                # AttachmentForm.slug = StringField()
                field = FieldList(CustomFormField(ProceduralFileSelectForm))
            elif prop == 'files':
                schema = schema_prop['schema']['schema']
                file_select_form = build_file_select_form(schema)
                field = FieldList(CustomFormField(file_select_form),
                                  min_entries=1)
            elif 'allowed' in schema_prop['schema']:
                choices = [(c, c) for c in schema_prop['schema']['allowed']]
                field = SelectMultipleField(choices=choices)
            else:
                field = SelectMultipleField(choices=[])
        elif 'allowed' in schema_prop:
            select = []
            for option in schema_prop['allowed']:
                select.append((str(option), str(option)))
            field = SelectField(choices=select)
        elif field_type == 'datetime':
            if form_prop.get('dateonly'):
                field = DateField(prop_name, default=date.today())
            else:
                field = DateTimeField(prop_name, default=datetime.now())
        elif field_type == 'integer':
            field = IntegerField(prop_name, default=0)
        elif field_type == 'float':
            field = FloatField(prop_name, default=0)
        elif field_type == 'boolean':
            field = BooleanField(prop_name)
        elif field_type == 'objectid' and 'data_relation' in schema_prop:
            if schema_prop['data_relation']['resource'] == 'files':
                field = FileSelectField(prop_name)
            else:
                field = StringField(prop_name)
        elif schema_prop.get('maxlength', 0) > 64:
            field = TextAreaField(prop_name)
        else:
            field = StringField(prop_name)

        setattr(form_class, prop_name, field)


def get_node_form(node_type):
    """Get a procedurally generated WTForm, based on the dyn_schema and
    node_schema of a specific node_type.
    :type node_type: dict
    :param node_type: Describes the node type via dyn_schema, form_schema and
    parent
    """
    class ProceduralForm(Form):
        pass

    node_schema = node_type['dyn_schema'].to_dict()
    form_prop = node_type['form_schema'].to_dict()
    parent_prop = node_type['parent']

    ProceduralForm.name = StringField('Name', validators=[DataRequired()])
    # Parenting
    if parent_prop:
        parent_names = ", ".join(parent_prop)
        ProceduralForm.parent = HiddenField('Parent ({0})'.format(parent_names))

    ProceduralForm.description = TextAreaField('Description')
    ProceduralForm.picture = FileSelectField('Picture', file_format='image')
    ProceduralForm.node_type = HiddenField(default=node_type['name'])

    add_form_properties(ProceduralForm, node_schema, form_prop)

    return ProceduralForm()


def recursive(path, rdict, data):
    item = path.pop(0)
    if not item in rdict:
        rdict[item] = {}
    if len(path) > 0:
        rdict[item] = recursive(path, rdict[item], data)
    else:
        rdict[item] = data
    return rdict


def process_node_form(form, node_id=None, node_type=None, user=None):
    """Generic function used to process new nodes, as well as edits
    """
    if not user:
        log.warning('process_node_form(node_id=%s) called while user not logged in', node_id)
        return False

    api = system_util.pillar_api()
    node_schema = node_type['dyn_schema'].to_dict()
    form_schema = node_type['form_schema'].to_dict()

    if node_id:
        # Update existing node
        node = pillarsdk.Node.find(node_id, api=api)
        node.name = form.name.data
        node.description = form.description.data
        if 'picture' in form:
            node.picture = form.picture.data
            if node.picture == 'None' or node.picture == '':
                node.picture = None
        if 'parent' in form:
            if form.parent.data != "":
                node.parent = form.parent.data

        def update_data(node_schema, form_schema, prefix=""):
            for pr in node_schema:
                schema_prop = node_schema[pr]
                form_prop = form_schema.get(pr, {})
                if pr == 'items':
                    continue
                if 'visible' in form_prop and not form_prop['visible']:
                    continue
                prop_name = "{0}{1}".format(prefix, pr)
                if schema_prop['type'] == 'dict':
                    update_data(
                        schema_prop['schema'],
                        form_prop['schema'],
                        "{0}__".format(prop_name))
                    continue
                data = form[prop_name].data
                if schema_prop['type'] == 'dict':
                    if data == 'None':
                        continue
                elif schema_prop['type'] == 'integer':
                    if data == '':
                        data = 0
                    else:
                        data = int(form[prop_name].data)
                elif schema_prop['type'] == 'datetime':
                    data = datetime.strftime(data,
                        app.config['RFC1123_DATE_FORMAT'])
                elif schema_prop['type'] == 'list':
                    if pr == 'attachments':
                        # data = json.loads(data)
                        data = [dict(field='description', files=data)]
                    elif pr == 'files':
                        # Only keep those items that actually refer to a file.
                        data = [file_item for file_item in data
                                if file_item.get('file')]
                    # elif pr == 'tags':
                    #     data = [tag.strip() for tag in data.split(',')]
                elif schema_prop['type'] == 'objectid':
                    if data == '':
                        # Set empty object to None so it gets removed by the
                        # SDK before node.update()
                        data = None
                else:
                    if pr in form:
                        data = form[prop_name].data
                path = prop_name.split('__')
                if len(path) > 1:
                    recursive_prop = recursive(
                        path, node.properties.to_dict(), data)
                    node.properties = recursive_prop
                else:
                    node.properties[prop_name] = data
        update_data(node_schema, form_schema)
        ok = node.update(api=api)
        if not ok:
            log.warning('Unable to update node: %s', node.error)
        # if form.picture.data:
        #     image_data = request.files[form.picture.name].read()
        #     post = node.replace_picture(image_data, api=api)
        return ok
    else:
        # Create a new node
        node = pillarsdk.Node()
        prop = {}
        files = {}
        prop['name'] = form.name.data
        prop['description'] = form.description.data
        prop['user'] = user
        if 'picture' in form:
            prop['picture'] = form.picture.data
            if prop['picture'] == 'None' or prop['picture'] == '':
                prop['picture'] = None
        if 'parent' in form:
            prop['parent'] = form.parent.data
        prop['properties'] = {}

        def get_data(node_schema, form_schema, prefix=""):
            for pr in node_schema:
                schema_prop = node_schema[pr]
                form_prop = form_schema.get(pr, {})
                if pr == 'items':
                    continue
                if 'visible' in form_prop and not form_prop['visible']:
                    continue
                prop_name = "{0}{1}".format(prefix, pr)
                if schema_prop['type'] == 'dict':
                    get_data(
                        schema_prop['schema'],
                        form_prop['schema'],
                        "{0}__".format(prop_name))
                    continue
                data = form[prop_name].data
                if schema_prop['type'] == 'media':
                    tmpfile = '/tmp/binary_data'
                    data.save(tmpfile)
                    binfile = open(tmpfile, 'rb')
                    files[pr] = binfile
                    continue
                if schema_prop['type'] == 'integer':
                    if data == '':
                        data = 0
                if schema_prop['type'] == 'list':
                    if data == '':
                        data = []
                if schema_prop['type'] == 'datetime':
                    data = datetime.strftime(data, app.config['RFC1123_DATE_FORMAT'])
                if schema_prop['type'] == 'objectid':
                    if data == '':
                        data = None
                path = prop_name.split('__')
                if len(path) > 1:
                    prop['properties'] = recursive(path, prop['properties'], data)
                else:
                    prop['properties'][prop_name] = data

        get_data(node_schema, form_schema)

        prop['node_type'] = form.node_type_id.data
        post = node.post(prop, api=api)

        return post
