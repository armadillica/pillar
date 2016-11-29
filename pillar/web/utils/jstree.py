from flask import Markup

from pillarsdk import Node
from pillarsdk.exceptions import ForbiddenAccess
from pillarsdk.exceptions import ResourceNotFound
from flask_login import current_user

from pillar.web import system_util

GROUP_NODES = {'group', 'storage', 'group_texture', 'group_hdri'}


def jstree_parse_node(node, children=None):
    """Generate JStree node from node object"""
    from pillar.web.nodes.routes import url_for_node

    node_type = node.node_type
    # Define better the node type
    if node_type == 'asset':
        node_type = node.properties.content_type

    parsed_node = dict(
        id="n_{0}".format(node._id),
        a_attr={"href": url_for_node(node=node)},
        li_attr={"data-node-type": node.node_type},
        text=Markup.escape(node.name),
        type=node_type,
        children=False)

    # Append children property only if it is a directory type
    if node_type in GROUP_NODES:
        parsed_node['children'] = True

    if node.permissions and node.permissions.world:
        parsed_node['li_attr']['is_free'] = True

    return parsed_node


def jstree_get_children(node_id, project_id=None):
    api = system_util.pillar_api()
    children_list = []
    lookup = {
        'projection': {
            'name': 1, 'parent': 1, 'node_type': 1, 'properties.order': 1,
            'properties.status': 1, 'properties.content_type': 1, 'user': 1,
            'project': 1},
        'sort': [('properties.order', 1), ('_created', 1)],
        'where': {
            '$and': [
                {'node_type': {'$regex': '^(?!attract_)'}},
                {'node_type': {'$not': {'$in': ['comment', 'post']}}},
            ],
        }
    }
    if node_id:
        if node_id.startswith('n_'):
            node_id = node_id.split('_')[1]
        lookup['where']['parent'] = node_id
    elif project_id:
        lookup['where']['project'] = project_id
        lookup['where']['parent'] = {'$exists': False}

    try:
        children = Node.all(lookup, api=api)
        for child in children['_items']:
            # TODO: allow nodes that don't have a status property to be visible
            # in the node tree (for example blog)
            is_pub = child.properties.status == 'published'
            if is_pub or (current_user.is_authenticated and child.user == current_user.objectid):
                children_list.append(jstree_parse_node(child))
    except ForbiddenAccess:
        pass
    return children_list


def jstree_build_children(node):
    return dict(
        id="n_{0}".format(node._id),
        text=Markup.escape(node.name),
        type=node.node_type,
        children=jstree_get_children(node._id)
    )


def jstree_build_from_node(node):
    """Give a node, traverse the tree bottom to top and expand the relevant
    branches.

    :param node: the base node, where tree building starts
    """
    api = system_util.pillar_api()
    # Parse the node and mark it as selected
    child_node = jstree_parse_node(node)
    child_node['state'] = dict(selected=True, opened=True)

    # Splice the specified child node between the other project children.
    def select_node(x):
        if x['id'] == child_node['id']:
            return child_node
        return x

    # Get the parent node
    parent = None
    if node.parent:
        try:
            parent = Node.find(node.parent, {
                'projection': {
                    'name': 1,
                    'node_type': 1,
                    'parent': 1,
                    'properties.content_type': 1,
                }}, api=api)
            # Define the child node of the tree (usually an asset)
        except ResourceNotFound:
            # If not found, we might be on the top level, in which case we skip the
            # while loop and use child_node
            pass
        except ForbiddenAccess:
            pass

    while parent:
        # Get the parent's parent
        parent_parent = jstree_parse_node(parent)
        # Get the parent's children (this will also include child_node)
        parent_children = [select_node(x) for x in jstree_get_children(parent_parent['id'])]
        parent_parent.pop('children', None)
        # Overwrite children_node with the current parent
        child_node = parent_parent
        # Set the node to open so that jstree actually displays the nodes
        child_node['state'] = dict(selected=True, opened=True)
        # Push in the computed children into the parent
        child_node['children'] = parent_children
        # If we have a parent
        if parent.parent:
            try:
                parent = Node.find(parent.parent, {
                    'projection': {
                        'name': 1, 'parent': 1, 'project': 1, 'node_type': 1},
                }, api=api)
            except ResourceNotFound:
                parent = None
        else:
            parent = None
    # Get top level nodes for the project
    project_children = jstree_get_children(None, node.project)

    nodes_list = [select_node(x) for x in project_children]
    return nodes_list
