from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms import BooleanField
from wtforms import HiddenField
from wtforms import TextAreaField
from wtforms import SelectField
from wtforms.validators import DataRequired
from wtforms.validators import Length
from pillarsdk.projects import Project
from pillarsdk import exceptions as sdk_exceptions
from pillar.web import system_util
from pillar.web.utils.forms import FileSelectField, JSONRequired


class ProjectForm(FlaskForm):
    project_id = HiddenField('project_id', validators=[DataRequired()])
    name = StringField('Name', validators=[DataRequired()])
    url = StringField('Url', validators=[DataRequired()])
    summary = StringField('Summary', validators=[Length(min=1, max=128)])
    description = TextAreaField('Description', validators=[DataRequired()])
    is_private = BooleanField('Private')
    category = SelectField('Category', choices=[
        ('film', 'Film'),
        ('course', 'Course'),
        ('workshop', 'Workshop'),
        ('assets', 'Assets')])
    status = SelectField('Status', choices=[
        ('published', 'Published'),
        ('pending', 'Pending'),
        ('deleted', 'Deleted')])
    picture_header = FileSelectField('Picture header', file_format='image')
    picture_square = FileSelectField('Picture square', file_format='image')
    picture_16_9 = FileSelectField('Picture 16:9', file_format='image')

    def validate(self):
        rv = FlaskForm.validate(self)
        if not rv:
            return False

        api = system_util.pillar_api()
        project = Project.find(self.project_id.data, api=api)
        if project.url == self.url.data:
            # Same URL as before, so that's fine.
            return True

        try:
            project_url = Project.find_one({'where': {'url': self.url.data}}, api=api)
        except sdk_exceptions.ResourceNotFound:
            # Not found, so the URL is fine.
            return True

        if project_url:
            self.url.errors.append('Sorry, project url already exists!')
            return False
        return True


class NodeTypeForm(FlaskForm):
    project_id = HiddenField('project_id', validators=[DataRequired()])
    name = StringField('Name', validators=[DataRequired()])
    parent = StringField('Parent')
    description = TextAreaField('Description')
    dyn_schema = TextAreaField('Schema', validators=[JSONRequired()])
    form_schema = TextAreaField('Form Schema', validators=[JSONRequired()])
    permissions = TextAreaField('Permissions', validators=[JSONRequired()])
