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
            description=shot.description,
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


class ShotForm(Form):
    name = TextField('Shot Name', validators=[DataRequired()])
    description = TextField('Description', validators=[DataRequired()])

@shots.route("/create", methods=('GET', 'POST'))
def create():
  form = ShotForm()
  if form.validate_on_submit():
      shot_type = NodeType.query.filter_by(name='shot').first()
      shot = Node(
        name=form.name.data,
        description=form.description.data,
        node_type_id=shot_type.id)
      db.session.add(shot)
      db.session.commit()
      return redirect('/')
  return render_template('shots/create.html', form=form)


@shots.route("/edit/<int:shot_id>", methods=('GET', 'POST'))
def edit(shot_id):
  shot = Node.query.get(shot_id) 
  form = ShotForm(
    name=shot.name,
    description=shot.description)
  if form.validate_on_submit():
      shot.name = form.name.data
      shot.description=form.description.data
      db.session.commit()
      return redirect('/')
  return render_template(
    'shots/edit.html', 
    form=form,
    shot_id=shot_id)


@shots.route("/delete/<int:shot_id>")
def delete(shot_id):
  shot = Node.query.get(shot_id)  
  if shot:
    db.session.delete(shot)
    return redirect('/')
  else:
    abort(404)
