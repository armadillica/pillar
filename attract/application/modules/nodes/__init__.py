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
from application.modules.nodes.forms import CustomFieldForm
from application.modules.nodes.forms import get_node_form
from application.modules.nodes.forms import process_node_form


# Name of the Blueprint
node_types = Blueprint('node_types', __name__)
nodes = Blueprint('nodes', __name__)

@node_types.route("/")
def index():
    """Display the node types
    """
    node_types = [t for t in NodeType.query.all()]

    return render_template('node_types/index.html',
        title='node_types',
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


@node_types.route("/add", methods=['GET', 'POST'])
def add():
    form = NodeTypeForm()

    if form.validate_on_submit():
        node_type = NodeType(
            name=form.name.data,
            description=form.description.data,
            url=form.url.data)

        db.session.add(node_type)
        db.session.commit()

        return redirect(url_for('node_types.index'))
    return render_template('node_types/add.html', form=form)


@node_types.route("/<int:node_type_id>/edit", methods=['GET', 'POST'])
def edit(node_type_id):
    node_type = NodeType.query.get_or_404(node_type_id)

    form = NodeTypeForm(obj=node_type)

    if form.validate_on_submit():
        node_type.name = form.name.data
        node_type.description = form.description.data
        node_type.url = form.url.data
        # Processing custom fields
        for field in form.custom_fields:
            print field.data['id']

        db.session.commit()
    else:
        print form.errors


    # if form.validate_on_submit():
    #     node_type = NodeType(
    #         name=form.name.data,
    #         description=form.description.data,
    #         url=form.url.data)

    #     db.session.add(node_type)
    #     db.session.commit()

    #     return redirect(url_for('node_types.index'))
    return render_template('node_types/edit.html', 
        node_type=node_type,
        form=form)



@nodes.route("/", methods=['GET', 'POST'])
def index():
    """Generic function to list all nodes
    """
    nodes = Node.query.all() 
    return render_template('nodes/index.html',
        nodes=nodes)


@nodes.route("/<node_type>/add", methods=['GET', 'POST'])
def add(node_type):
    """Generic function to add a node of any type
    """
    form = get_node_form(node_type) 
    if form.validate_on_submit():
        if process_node_form(form):
            return redirect('/')
    else:
        print form.errors
    return render_template('nodes/add.html',
        node_type=node_type,
        form=form)


@nodes.route("/<int:node_id>/edit", methods=['GET', 'POST'])
def edit(node_id):
    """Generic node editing form
    """
    node = Node.query.get_or_404(node_id)
    form = get_node_form(node.node_type.url)

    if form.validate_on_submit():
        if process_node_form(form, node_id):
            return redirect(url_for('node.edit', node_id=node_id))

    form.name.data = node.name
    form.description.data = node.description

    # We populate the form, basing ourselves on the default node properties
    for node_property in node.properties:
        for field in form:
            if field.name == node_property.custom_field.name_url:
                value = node_property.value
                # We cast values into the right type
                if node_property.custom_field.field_type == 'integer':
                    value = int(value)
                if node_property.custom_field.field_type == 'select':
                    value = int(value)
                field.data = value


    return render_template('nodes/edit.html',
        node=node,
        form=form)


@nodes.route("/<int:node_id>/delete", methods=['GET', 'POST'])
def delete(node_id):
    """Generic node deletion
    """
    node = Node.query.get_or_404(node_id)
    db.session.delete(node)
    db.session.commit()
    return 'ok'
