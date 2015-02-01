from flask import abort
from flask import Blueprint
from flask import jsonify
from flask import render_template
from flask import redirect
from flask import request
from flask import flash
from flask import url_for

from application import db

from application.modules.nodes.models import Node, NodeType
from application.modules.nodes.forms import NodeTypeForm


# Name of the Blueprint
nodes = Blueprint('nodes', __name__)

@nodes.route("/")
def index():
    """Display the node types
    """
    node_types = [t for t in NodeType.query.all()]

    return render_template('nodes/index.html',
        title='nodes',
        node_types=node_types)

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


@nodes.route("/create", methods=('GET', 'POST'))
def create():
    form = NodeTypeForm()

    if form.validate_on_submit():
        node_type = NodeType(
            name=form.name.data,
            description=form.description.data,
            url=form.url.data)

        db.session.add(node_type)
        db.session.commit()

        return redirect(url_for('nodes.index'))
    return render_template('nodes/create.html', form=form)
