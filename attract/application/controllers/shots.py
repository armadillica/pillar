from flask import (abort,
                   Blueprint,
                   jsonify,
                   render_template,
                   redirect,
                   request)

from flask.ext.thumbnails import Thumbnail
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.orm import aliased

from flask_wtf import Form
from wtforms import TextField, BooleanField
from wtforms.validators import DataRequired

from application import db

from application.models.model import (
    Node,
    NodeType)

# Name of the Blueprint
shots = Blueprint('shots', __name__)

@shots.route("/")
def index():
    shots = []
    for shot in Node.query.\
        join(NodeType).\
        filter(NodeType.url == 'shot'):
        status = None
        if shot.status:
            status = shot.status.name
        shots.append(dict(
            id=shot.id,
            name=shot.name,
            status=status))
    return render_template('shots/index.html', 
        title='shots',
        shots=shots)


@shots.route("/view/<int:shot_id>")
def view(shot_id):
  shot = Node.query.get(shot_id)  
  if shot and shot.node_type.url == 'shot':
    return render_template('shots/view.html', 
      title='shots',
      shot=shot)
  else:
    abort(404)

"""
class ShotForm(Form):
    name = TextField('Blender-ID')
    description = TextField('First Name', validators=[DataRequired()])
    parent_id = IntegerFiled('Last Name', validators=[DataRequired()])
    cloud_communications = BooleanField('Cloud Communications')
"""
@shots.route("/create")
def create():
  return 'create here'
