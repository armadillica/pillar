import json
from flask import g
from flask import abort
from flask import request

from bson import ObjectId

# from application import app


def permissions_lookup(action, lookup):
    type_world_permissions = g.get('type_world_permissions')
    type_owner_permissions = g.get('type_owner_permissions')
    node_types = []
    # Get all node_types allowed by world:
    for perm in type_world_permissions:
        if action in type_world_permissions[perm]:
            node_types.append(str(perm))
    # Get all nodes with node_type allowed by owner if user == owner
    owner_lookup = []
    for perm in type_owner_permissions:
        if action in type_owner_permissions[perm]:
            if action not in type_world_permissions[perm]:
                # If one of the following is true
                # If node_type==node_type and user==user
                owner_lookup.append(
                    {'$and': [{'node_type': str(perm)},
                              {'user': str(g.get('token_data')['user'])}]})
    lookup['$or'] = [{'node_type': {'$in': node_types}}]
    if len(owner_lookup) > 0:
        lookup['$or'].append({'$or': owner_lookup})
    return lookup


def pre_GET(request, lookup, data_driver):
    action = 'GET'
    if 'token_type' not in lookup and '_id' not in request.view_args:
        # Is quering for all nodes (mixed types)
        lookup = permissions_lookup(action, lookup)
    else:
        # Is quering for one specific node
        if action not in g.get('world_permissions') and \
                action not in g.get('groups_permissions'):
            lookup['user'] = g.get('token_data')['user']
    # token_data = validate_token()
    # validate(token_data['token'])

    # lookup["userr"] = "user"
    # print ("Lookup")
    # print (lookup)


def pre_PUT(request, lookup, data_driver):
    action = 'UPDATE'
    if 'token_type' not in lookup and '_id' not in request.view_args:
        # Is updating all nodes (mixed types)
        lookup = permissions_lookup(action, lookup)
    else:
        # Is updating one specific node
        if action not in g.get('world_permissions') and \
                action not in g.get('groups_permissions'):
            lookup['user'] = g.get('token_data')['user']

    # print ("Lookup")
    # print (lookup)


def pre_PATCH(request, lookup, data_driver):
    print ("Patch")


def pre_POST(request, data_driver):
    # Only Post allowed documents
    action = 'POST'
    print (g.get('type_groups_permissions'))
    # Is quering for one specific node
    if action not in g.get('world_permissions') and \
            action not in g.get('groups_permissions'):
        abort(403)


def pre_DELETE(request, lookup, data_driver):
    type_world_permissions = g.get('type_world_permissions')
    type_owner_permissions = g.get('type_owner_permissions')
    type_groups_permissions = g.get('type_groups_permissions')
    action = 'DELETE'

    if '_id' in lookup:
        nodes = data_driver.db['nodes']
        dbnode = nodes.find_one({'_id': ObjectId(lookup['_id'])})
        # print (dbnode.count())
        node_type = str(dbnode['node_type'])
        if g.get('token_data')['user'] == dbnode['user']:
            owner = True
        else:
            owner = False
        if action not in type_world_permissions[node_type] and \
            action not in type_groups_permissions[node_type]:
            if action not in type_owner_permissions[node_type]:
                print ("Abort1")
                abort(403)
            else:
                if not owner:
                    print ("Abort2")
                    abort(403)
    else:
        print ("Abort3")
        abort(403)


def compute_permissions(user, data_driver):
    node_type = None
    dbnode = None
    owner_permissions = []
    world_permissions = []
    groups_permissions = []
    groups = data_driver.db['groups']
    users = data_driver.db['users']
    # The hardcoded owners group. In this group we define the default permission
    # level that the user associated with a node has. These permissions can be
    # overridden by custom group and world.
    owner_group = groups.find_one({'name': 'owner'})
    # The world group is always evaluated, especially when the user is not logged
    # in.
    world_group = groups.find_one({'name': 'world'})
    user_data = users.find_one({'_id': ObjectId(user)})
    # If we are requesting a specific node
    try:
        uuid = request.path.split("/")[2]
        nodes = data_driver.db['nodes']
        lookup = {'_id': ObjectId(uuid)}
        dbnode = nodes.find_one(lookup)
    except IndexError:
        pass
    if dbnode:
        # If a node object is found, extract the node_type ObjectID
        node_type = str(dbnode['node_type'])

    # If we are creating a new node, we get the node_type ObjectID from the request
    json_data = None
    # TODO(fsiddi): handle creation vs everything else in a more efficient way
    try:
        json_data = json.loads(request.data)
    except ValueError:
        pass
    if not node_type and json_data:
        if 'node_type' in json_data:
            node_type = json_data['node_type']

    # Extract query lookup
    # which node_type is asking for?
    # TODO(fsiddi): It's not clear if this code is being used at all

    # for arg in request.args:
    #     if arg == 'where':
    #         try:
    #             where = json.loads(request.args[arg])
    #         except ValueError:
    #             raise
    #         if where.get('node_type'):
    #             node_type = where.get('node_type')
    #         break

    # Get and store permissions for that node_type
    type_owner_permissions = {}
    type_world_permissions = {}
    type_groups_permissions = {}
    type_mixed_permissions = {}

    for perm in owner_group['permissions']:
        # Build the global type_owner_permission dictionary
        type_owner_permissions[str(perm['node_type'])] = perm['permissions']
        if str(perm['node_type']) == node_type:
            # If a node_type ObjectID matches the requested node_type, populate
            # the actual owner permissions for the current user
            owner_permissions = perm['permissions']

    for perm in world_group['permissions']:
        # Build the global type_owner_permission dictionary
        type_world_permissions[str(perm['node_type'])] = perm['permissions']
        if str(perm['node_type']) == node_type:
            # If a node_type ObjectID matches the requested node_type, populate
            # the actual world permissions in relation to the current user
            world_permissions = perm['permissions']

        # Adding empty permissions
        if str(perm['node_type']) not in type_groups_permissions:
            type_groups_permissions[str(perm['node_type'])] = []

    # This dictionary will hold the combined permissions. Why?
    type_mixed_permissions = type_world_permissions

    # Get group ObjectID associated with the requesting user
    groups_data = user_data.get('groups')
    if groups_data:
        for group in groups_data:
            group_data = groups.find_one({'_id': ObjectId(group)})
            for perm in group_data['permissions']:
                # Populate the group permissions. This searches in the
                # type_groups_permissions dict, which is generated previously
                # using the world permissions. If a world permission is not
                # defined for a certain node type, this will fail.
                type_groups_permissions[str(perm['node_type'])] += \
                    perm['permissions']
                type_mixed_permissions[str(perm['node_type'])] += \
                    perm['permissions']
                if str(perm['node_type']) == node_type:
                    groups_permissions = perm['permissions']

    return {
        'owner_permissions': owner_permissions,
        'world_permissions': world_permissions,
        'groups_permissions': groups_permissions,
        'type_owner_permissions': type_owner_permissions,
        'type_world_permissions': type_world_permissions,
        'type_groups_permissions': type_groups_permissions,
        'type_mixed_permissions': type_mixed_permissions
    }


def check_permissions(user, data_driver):
    # Entry point should be nodes
    entry_point = request.path.split("/")[1]
    if entry_point != 'nodes':
        return

    permissions = compute_permissions(user, data_driver)

    # Store permission properties on global
    setattr(g, 'owner_permissions', permissions['owner_permissions'])
    setattr(g, 'world_permissions', permissions['world_permissions'])
    setattr(g, 'groups_permissions', permissions['groups_permissions'])
    setattr(g, 'type_owner_permissions', permissions['type_owner_permissions'])
    setattr(g, 'type_world_permissions', permissions['type_world_permissions'])
    setattr(g, 'type_groups_permissions', permissions['type_groups_permissions'])
