from flask import request
from flask import jsonify
from flask_login import login_required, current_user
from pillarsdk import Node
from pillar.web.utils import system_util
from ..routes import blueprint


@blueprint.route('/groups/create', methods=['POST'])
@login_required
def groups_create():
    # Use current_project_id from the session instead of the cookie
    name = request.form['name']
    project_id = request.form['project_id']
    parent_id = request.form.get('parent_id')

    api = system_util.pillar_api()
    # We will create the Node object later on, after creating the file object
    node_asset_props = dict(
        name=name,
        user=current_user.objectid,
        node_type='group',
        project=project_id,
        properties=dict(
            status='published'))
    # Add parent_id only if provided (we do not provide it when creating groups
    # at the Project root)
    if parent_id:
        node_asset_props['parent'] = parent_id

    node_asset = Node(node_asset_props)
    node_asset.create(api=api)
    return jsonify(
        status='success',
        data=dict(name=name, asset_id=node_asset._id))
