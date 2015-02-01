from flask_wtf import Form
from wtforms import TextField
from wtforms import BooleanField
from wtforms import SelectField
from wtforms import TextAreaField
from wtforms import IntegerField

from wtforms.validators import DataRequired

from application.modules.nodes.models import Node, NodeType

class ShotForm(Form):
    statuses = Node.query\
        .join(NodeType)\
        .filter(NodeType.url == 'shot_status')\
        .all()

    name = TextField('Shot Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    status_id = SelectField('Status',
        coerce=int, 
        choices=[(status.id, status.name) for status in statuses])
    duration = IntegerField('Duration')
    notes = TextAreaField('Notes')
