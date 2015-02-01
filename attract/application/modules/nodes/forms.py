from flask_wtf import Form
from wtforms import TextField
from wtforms import BooleanField
from wtforms import SelectField
from wtforms import TextAreaField
from wtforms import IntegerField

from wtforms.validators import DataRequired

from application.modules.nodes.models import Node, NodeType

class NodeTypeForm(Form):
    name = TextField('Node Name', validators=[DataRequired()])
    url = TextField('Url', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    is_extended = BooleanField('Is extended')