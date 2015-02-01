from flask_wtf import Form
from wtforms import TextField
from wtforms import BooleanField
from wtforms import SelectField
from wtforms import TextAreaField
from wtforms import IntegerField

from wtforms.validators import DataRequired

class ShotForm(Form):
    name = TextField('Shot Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    status_id = SelectField('Status', coerce=int)
    duration = IntegerField('Duration')
    notes = TextAreaField('Notes')
