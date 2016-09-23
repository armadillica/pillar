import copy
import logging

log = logging.getLogger(__name__)


def assign_permissions(project, node_types, permission_callback):
    """Generator, yields the node types with certain permissions set.

    The permission_callback is called for each node type, and each user
    and group permission in the project, and should return the appropriate
    extra permissions for that node type.

    Yields copies of the given node types with new permissions.

    permission_callback(node_type, uwg, ident, proj_methods) is returned, where
    - 'node_type' is the node type dict
    - 'ugw' is either 'user', 'group', or 'world',
    - 'ident' is the group or user ID, or None when ugw is 'world',
    - 'proj_methods' is the list of already-allowed project methods.
    """

    proj_perms = project['permissions']

    for nt in node_types:
        permissions = {}

        for key in ('users', 'groups'):
            perms = proj_perms[key]
            singular = key.rstrip('s')

            for perm in perms:
                assert isinstance(perm, dict), 'perm should be dict, but is %r' % perm
                ident = perm[singular]  # group or user ID.

                methods_to_allow = permission_callback(nt, singular, ident, perm['methods'])
                if not methods_to_allow:
                    continue

                permissions.setdefault(key, []).append(
                    {singular: ident,
                     'methods': methods_to_allow}
                )

        # World permissions are simpler.
        world_methods_to_allow = permission_callback(nt, 'world', None,
                                                     permissions.get('world', []))
        if world_methods_to_allow:
            permissions.setdefault('world', []).extend(world_methods_to_allow)

        node_type = copy.deepcopy(nt)
        if permissions:
            node_type['permissions'] = permissions
        yield node_type


def add_to_project(project, node_types, replace_existing):
    """Adds the given node types to the project.

    Overwrites any existing by the same name when replace_existing=True.
    """

    project_id = project['_id']

    for node_type in node_types:
        found = [nt for nt in project['node_types']
                 if nt['name'] == node_type['name']]
        if found:
            assert len(found) == 1, 'node type name should be unique (found %ix)' % len(found)

            # TODO: validate that the node type contains all the properties Attract needs.
            if replace_existing:
                log.info('Replacing existing node type %s on project %s',
                         node_type['name'], project_id)
                project['node_types'].remove(found[0])
            else:
                continue

        project['node_types'].append(node_type)
