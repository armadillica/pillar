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
from application.modules.nodes.models import Node, NodeType, NodeProperties
from application.modules.shots.models import NodeShot


# Name of the Blueprint
shots = Blueprint('shots', __name__)

@shots.route("/")
def index():
    shots = []

    for n in Node.query.all():
        for p in n.properties:
            print p.value

    for shot in Node.query.\
        join(NodeType).\
        filter(NodeType.url == 'shot'):
        status = None
        # if shot.status:
        #     status = shot.status.name
        s = dict(
            id=shot.id,
            name=shot.name,
            description=shot.description)
        for node_property in shot.properties:
            s[node_property.custom_field.name_url] = node_property.value
        shots.append(s)
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
            notes=shot.get_property('notes'))
    else:
        abort(404)


@shots.route("/add", methods=('GET', 'POST'))
def add():
    form = ShotForm()

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
    return render_template('shots/add.html', form=form)



@shots.route("/procedural", methods=('GET', 'POST'))
def procedural():
    from flask_wtf import Form
    from wtforms import TextField
    from wtforms import BooleanField
    from wtforms import SelectField
    from wtforms import TextAreaField
    from wtforms import IntegerField
    from wtforms import HiddenField

    from application.modules.nodes.models import CustomFields
    from wtforms.validators import DataRequired

    node_type = NodeType.query.filter_by(url='shot').first()
    class ProceduralForm(Form):
        pass

    setattr(ProceduralForm,
        'name',
        TextField('Node Name', validators=[DataRequired()]))
    setattr(ProceduralForm,
        'description',
        TextAreaField('Description', validators=[DataRequired()]))
    setattr(ProceduralForm,
        'node_type_id',
        HiddenField(default=node_type.id))

    for custom_field in CustomFields.query\
        .join(NodeType)\
        .filter(NodeType.url == 'shot'):
        
        if custom_field.field_type == 'text':
            field_properties = TextAreaField(custom_field.name, 
                validators=[DataRequired()])
        elif custom_field.field_type == 'integer':
            field_properties = IntegerField(custom_field.name, 
                validators=[DataRequired()])
        elif custom_field.field_type == 'select':
            options = Node.query\
                .join(NodeType)\
                .filter(NodeType.url==custom_field.name_url)\
                .all()
            print options
            field_properties = SelectField(custom_field.name, 
                coerce=int,
                choices=[(option.id, option.name) for option in options] )
                #choices=[(status.id, status.name) for status in statuses])
        
        setattr(ProceduralForm, custom_field.name_url, field_properties)

    form = ProceduralForm()

    if form.validate_on_submit():
        node = Node(
            name=form.name.data,
            description=form.description.data,
            node_type_id=form.node_type_id.data)
        db.session.add(node)
        db.session.commit()

        for custom_field in CustomFields.query\
            .join(NodeType)\
            .filter(NodeType.url == 'shot'):

            for field in form:
                if field.name == custom_field.name_url:
                    node_property = NodeProperties(
                        node_id=node.id,
                        custom_field_id=custom_field.id,
                        value=field.data)
                    db.session.add(node_property)
                    db.session.commit()

        return redirect('/')
    else:
        print form.errors
    # if form.validate_on_submit():
    #     shot_type = NodeType.query.filter_by(url='shot').first()
    #     shot = Node(
    #         name=form.name.data,
    #         description=form.description.data,
    #         node_type_id=shot_type.id,
    #         status_id=form.status_id.data)
    #     # Create entry in the attached node table
    #     shot.node_shot = [NodeShot(
    #         duration=form.duration.data, 
    #         notes=form.notes.data)]

    #     db.session.add(shot)
    #     db.session.commit()
    #     return redirect('/')
    return render_template('shots/procedural.html', form=form)


@shots.route("/edit/<int:shot_id>", methods=('GET', 'POST'))
def edit(shot_id):
    shot = Node.query.get(shot_id)

    form = ShotForm(
        name=shot.name,
        description=shot.description,
        duration=shot.node_shot[0].duration,
        note=shot.node_shot[0].notes)

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
