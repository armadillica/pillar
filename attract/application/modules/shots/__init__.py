from flask import (abort,
                   Blueprint,
                   jsonify,
                   render_template,
                   redirect,
                   request,
                   flash)

from flask.ext.thumbnails import Thumbnail
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.orm import aliased

from application import db

from application.modules.shots.forms import ShotForm
from application.modules.nodes.models import Node, NodeType, Status
from application.modules.shots.models import NodeShot


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
            duration=shot.node_shot[0].duration,
            status=status,
            notes=shot.node_shot[0].notes))
    return render_template('shots/index.html', 
        title='shots',
        shots=shots)


@shots.route("/view/<int:shot_id>")
def view(shot_id):
    shot = Node.query.get(shot_id)  
    if shot and shot.node_type.url == 'shot':
        return render_template('shots/view.html', 
            title='shots',
            shot=shot,
            notes=shot.node_shot[0].notes)
    else:
        abort(404)


@shots.route("/create", methods=('GET', 'POST'))
def create():
    form = ShotForm()
    # Populate dropdown select with available Statuses
    form.status_id.choices = [(status.id, status.name) for status in Status.query.all()]
    if form.validate_on_submit():
        shot_type = NodeType.query.filter_by(url='shot').first()
        shot = Node(
            name=form.name.data,
            description=form.description.data,
            node_type_id=shot_type.id,
            status_id=form.status_id.data)
        # Create entry in the attached node table
        shot.node_shot = [NodeShot(
            duration=form.duration.data, 
            notes=form.notes.data)]

        db.session.add(shot)
        db.session.commit()
        return redirect('/')
    return render_template('shots/create.html', form=form)


@shots.route("/edit/<int:shot_id>", methods=('GET', 'POST'))
def edit(shot_id):
    shot = Node.query.get(shot_id)

    form = ShotForm(
        name=shot.name,
        description=shot.description,
        duration=shot.node_shot[0].duration,
        note=shot.node_shot[0].notes)
    form.status_id.choices = [(status.id, status.name) for status in Status.query.all()]

    if form.validate_on_submit():
        print shot.node_shot
        shot.name = form.name.data
        shot.description = form.description.data
        shot.node_shot[0].duration = form.duration.data
        shot.status_id = form.status_id.data
        shot.node_shot[0].notes = form.notes.data
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
        db.session.commit()
        return redirect('/')
    else:
        abort(404)
