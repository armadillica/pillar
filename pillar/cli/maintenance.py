import copy
import datetime
import logging
import typing

import bson.tz_util
from bson import ObjectId
from bson.errors import InvalidId
from flask_script import Manager

from pillar import current_app

# Collections to skip when finding file references (during orphan file detection).
# This collection can be added to from PillarExtension.setup_app().
ORPHAN_FINDER_SKIP_COLLECTIONS = {
    # Skipping the files collection under the assumption that we have no files
    # referencing other files.
    'files',

    # Authentication tokens never refer to files, and it's a big collection so
    # good to skip.
    'tokens',
}

log = logging.getLogger(__name__)

manager_maintenance = Manager(
    current_app, usage="Maintenance scripts, to update user groups")


@manager_maintenance.command
def find_duplicate_users():
    """Finds users that have the same BlenderID user_id."""

    from collections import defaultdict

    users_coll = current_app.data.driver.db['users']
    nodes_coll = current_app.data.driver.db['nodes']
    projects_coll = current_app.data.driver.db['projects']

    found_users = defaultdict(list)

    for user in users_coll.find():
        blender_ids = [auth['user_id'] for auth in user['auth']
                       if auth['provider'] == 'blender-id']
        if not blender_ids:
            continue
        blender_id = blender_ids[0]
        found_users[blender_id].append(user)

    for blender_id, users in found_users.items():
        if len(users) == 1:
            continue

        usernames = ', '.join(user['username'] for user in users)
        print('Blender ID: %5s has %i users: %s' % (
            blender_id, len(users), usernames))

        for user in users:
            print('  %s owns %i nodes and %i projects' % (
                user['username'],
                nodes_coll.count({'user': user['_id']}),
                projects_coll.count({'user': user['_id']}),
            ))


@manager_maintenance.command
def sync_role_groups(do_revoke_groups):
    """For each user, synchronizes roles and group membership.

    This ensures that everybody with the 'subscriber' role is also member of the 'subscriber'
    group, and people without the 'subscriber' role are not member of that group. Same for
    admin and demo groups.

    When do_revoke_groups=False (the default), people are only added to groups.
    when do_revoke_groups=True, people are also removed from groups.
    """

    from pillar.api import service

    if do_revoke_groups not in {'true', 'false'}:
        print('Use either "true" or "false" as first argument.')
        print('When passing "false", people are only added to groups.')
        print('when passing "true", people are also removed from groups.')
        raise SystemExit()
    do_revoke_groups = do_revoke_groups == 'true'

    service.fetch_role_to_group_id_map()

    users_coll = current_app.data.driver.db['users']
    groups_coll = current_app.data.driver.db['groups']

    group_names = {}

    def gname(gid):
        try:
            return group_names[gid]
        except KeyError:
            name = groups_coll.find_one(gid, projection={'name': 1})['name']
            name = str(name)
            group_names[gid] = name
            return name

    ok_users = bad_users = 0
    for user in users_coll.find():
        grant_groups = set()
        revoke_groups = set()
        current_groups = set(user.get('groups', []))
        user_roles = user.get('roles', set())

        for role in service.ROLES_WITH_GROUPS:
            action = 'grant' if role in user_roles else 'revoke'
            groups = service.manage_user_group_membership(user, role, action)

            if groups is None:
                # No changes required
                continue

            if groups == current_groups:
                continue

            grant_groups.update(groups.difference(current_groups))
            revoke_groups.update(current_groups.difference(groups))

        if grant_groups or revoke_groups:
            bad_users += 1

            expected_groups = current_groups.union(grant_groups).difference(revoke_groups)

            print('Discrepancy for user %s/%s:' % (user['_id'], user['full_name'].encode('utf8')))
            print('    - actual groups  :', sorted(gname(gid) for gid in user.get('groups')))
            print('    - expected groups:', sorted(gname(gid) for gid in expected_groups))
            print('    - will grant     :', sorted(gname(gid) for gid in grant_groups))

            if do_revoke_groups:
                label = 'WILL REVOKE '
            else:
                label = 'could revoke'
            print('    - %s   :' % label, sorted(gname(gid) for gid in revoke_groups))

            if grant_groups and revoke_groups:
                print('        ------ CAREFUL this one has BOTH grant AND revoke -----')

            # Determine which changes we'll apply
            final_groups = current_groups.union(grant_groups)
            if do_revoke_groups:
                final_groups.difference_update(revoke_groups)
            print('    - final groups   :', sorted(gname(gid) for gid in final_groups))

            # Perform the actual update
            users_coll.update_one({'_id': user['_id']},
                                  {'$set': {'groups': list(final_groups)}})
        else:
            ok_users += 1

    print('%i bad and %i ok users seen.' % (bad_users, ok_users))


@manager_maintenance.command
def sync_project_groups(user_email, fix):
    """Gives the user access to their self-created projects."""

    if fix.lower() not in {'true', 'false'}:
        print('Use either "true" or "false" as second argument.')
        print('When passing "false", only a report is produced.')
        print('when passing "true", group membership is fixed.')
        raise SystemExit()
    fix = fix.lower() == 'true'

    users_coll = current_app.data.driver.db['users']
    proj_coll = current_app.data.driver.db['projects']
    groups_coll = current_app.data.driver.db['groups']

    # Find by email or by user ID
    if '@' in user_email:
        where = {'email': user_email}
    else:
        try:
            where = {'_id': ObjectId(user_email)}
        except InvalidId:
            log.warning('Invalid ObjectID: %s', user_email)
            return

    user = users_coll.find_one(where, projection={'_id': 1, 'groups': 1})
    if user is None:
        log.error('User %s not found', where)
        raise SystemExit()

    user_groups = set(user['groups'])
    user_id = user['_id']
    log.info('Updating projects for user %s', user_id)

    ok_groups = missing_groups = 0
    for proj in proj_coll.find({'user': user_id}):
        project_id = proj['_id']
        log.info('Investigating project %s (%s)', project_id, proj['name'])

        # Find the admin group
        admin_group = groups_coll.find_one({'name': str(project_id)}, projection={'_id': 1})
        if admin_group is None:
            log.warning('No admin group for project %s', project_id)
            continue
        group_id = admin_group['_id']

        # Check membership
        if group_id not in user_groups:
            log.info('Missing group membership')
            missing_groups += 1
            user_groups.add(group_id)
        else:
            ok_groups += 1

    log.info('User %s was missing %i group memberships; %i projects were ok.',
             user_id, missing_groups, ok_groups)

    if missing_groups > 0 and fix:
        log.info('Updating database.')
        result = users_coll.update_one({'_id': user_id},
                                       {'$set': {'groups': list(user_groups)}})
        log.info('Updated %i user.', result.modified_count)


@manager_maintenance.command
def check_home_project_groups():
    """Checks all users' group membership of their home project admin group."""

    users_coll = current_app.data.driver.db['users']
    proj_coll = current_app.data.driver.db['projects']

    good = bad = 0
    for proj in proj_coll.find({'category': 'home'}):
        try:
            admin_group_perms = proj['permissions']['groups'][0]
        except IndexError:
            log.error('Project %s has no admin group', proj['_id'])
            return 255
        except KeyError:
            log.error('Project %s has no group permissions at all', proj['_id'])
            return 255

        user = users_coll.find_one({'_id': proj['user']},
                                   projection={'groups': 1})
        if user is None:
            log.error('Project %s has non-existing owner %s', proj['user'])
            return 255

        user_groups = set(user['groups'])
        admin_group_id = admin_group_perms['group']
        if admin_group_id in user_groups:
            # All is fine!
            good += 1
            continue

        log.warning('User %s has no admin rights to home project %s -- needs group %s',
                    proj['user'], proj['_id'], admin_group_id)
        bad += 1

    log.info('%i projects OK, %i projects in error', good, bad)
    return bad


@manager_maintenance.command
@manager_maintenance.option('-c', '--chunk', dest='chunk_size', default=50,
                            help='Number of links to update, use 0 to update all.')
@manager_maintenance.option('-q', '--quiet', dest='quiet', action='store_true', default=False)
@manager_maintenance.option('-w', '--window', dest='window', default=12,
                            help='Refresh links that expire in this many hours.')
def refresh_backend_links(backend_name, chunk_size=50, quiet=False, window=12):
    """Refreshes all file links that are using a certain storage backend.

    Use `--chunk 0` to refresh all links.
    """

    chunk_size = int(chunk_size)
    window = int(window)

    loglevel = logging.WARNING if quiet else logging.DEBUG
    logging.getLogger('pillar.api.file_storage').setLevel(loglevel)

    chunk_size = int(chunk_size)  # CLI parameters are passed as strings
    from pillar.api import file_storage

    file_storage.refresh_links_for_backend(backend_name, chunk_size, window * 3600)


@manager_maintenance.command
def expire_all_project_links(project_uuid):
    """Expires all file links for a certain project without refreshing.

    This is just for testing.
    """

    import datetime
    import bson.tz_util

    files_collection = current_app.data.driver.db['files']

    now = datetime.datetime.now(tz=bson.tz_util.utc)
    expires = now - datetime.timedelta(days=1)

    result = files_collection.update_many(
        {'project': ObjectId(project_uuid)},
        {'$set': {'link_expires': expires}}
    )

    print('Expired %i links' % result.matched_count)


@manager_maintenance.command
@manager_maintenance.option('-p', '--project', dest='proj_url', nargs='?',
                            help='Project URL')
@manager_maintenance.option('-a', '--all', dest='all_projects', action='store_true', default=False,
                            help='Replace on all projects.')
@manager_maintenance.option('-m', '--missing', dest='missing',
                            action='store_true', default=False,
                            help='Add missing node types. Note that this may add unwanted ones.')
def replace_pillar_node_type_schemas(proj_url=None, all_projects=False, missing=False):
    """Replaces the project's node type schemas with the standard Pillar ones.

    Non-standard node types are left alone.
    """

    if bool(proj_url) == all_projects:
        log.error('Use either --project or --all.')
        return 1

    from pillar.api.utils.authentication import force_cli_user
    force_cli_user()

    from pillar.api.node_types import PILLAR_NAMED_NODE_TYPES
    from pillar.api.utils import remove_private_keys

    projects_collection = current_app.db()['projects']

    def handle_project(project):
        log.info('Handling project %s', project['url'])
        is_public_proj = not project.get('is_private', True)

        for proj_nt in project['node_types']:
            nt_name = proj_nt['name']
            try:
                pillar_nt = PILLAR_NAMED_NODE_TYPES[nt_name]
            except KeyError:
                log.info('   - skipping non-standard node type "%s"', nt_name)
                continue

            log.info('   - replacing schema on node type "%s"', nt_name)

            # This leaves node type keys intact that aren't in Pillar's node_type_xxx definitions,
            # such as permissions.
            proj_nt.update(copy.deepcopy(pillar_nt))

            # On our own public projects we want to be able to set license stuff.
            if is_public_proj:
                proj_nt['form_schema'].pop('license_type', None)
                proj_nt['form_schema'].pop('license_notes', None)

        # Find new node types that aren't in the project yet.
        if missing:
            project_ntnames = set(nt['name'] for nt in project['node_types'])
            for nt_name in set(PILLAR_NAMED_NODE_TYPES.keys()) - project_ntnames:
                log.info('   - Adding node type "%s"', nt_name)
                pillar_nt = PILLAR_NAMED_NODE_TYPES[nt_name]
                project['node_types'].append(copy.deepcopy(pillar_nt))

        # Use Eve to PUT, so we have schema checking.
        db_proj = remove_private_keys(project)
        r, _, _, status = current_app.put_internal('projects', db_proj, _id=project['_id'])
        if status != 200:
            log.error('Error %i storing altered project %s %s', status, project['_id'], r)
            raise SystemExit('Error storing project, see log.')
        log.info('Project saved succesfully.')

    if all_projects:
        for project in projects_collection.find():
            handle_project(project)
        return

    project = projects_collection.find_one({'url': proj_url})
    if not project:
        log.error('Project url=%s not found', proj_url)
        return 3

    handle_project(project)


@manager_maintenance.command
def remarkdown_comments():
    """Retranslates all Markdown to HTML for all comment nodes.
    """

    from pillar.api.nodes import convert_markdown

    nodes_collection = current_app.db()['nodes']
    comments = nodes_collection.find({'node_type': 'comment'},
                                     projection={'properties.content': 1,
                                                 'node_type': 1})

    updated = identical = skipped = errors = 0
    for node in comments:
        convert_markdown(node)
        node_id = node['_id']

        try:
            content_html = node['properties']['content_html']
        except KeyError:
            log.warning('Node %s has no content_html', node_id)
            skipped += 1
            continue

        result = nodes_collection.update_one(
            {'_id': node_id},
            {'$set': {'properties.content_html': content_html}}
        )
        if result.matched_count != 1:
            log.error('Unable to update node %s', node_id)
            errors += 1
            continue

        if result.modified_count:
            updated += 1
        else:
            identical += 1

    log.info('updated  : %i', updated)
    log.info('identical: %i', identical)
    log.info('skipped  : %i', skipped)
    log.info('errors   : %i', errors)


@manager_maintenance.command
@manager_maintenance.option('-p', '--project', dest='proj_url', nargs='?',
                            help='Project URL')
@manager_maintenance.option('-a', '--all', dest='all_projects', action='store_true', default=False,
                            help='Replace on all projects.')
def upgrade_attachment_schema(proj_url=None, all_projects=False):
    """Replaces the project's attachments with the new schema.

    Updates both the schema definition and the nodes with attachments (asset, page, post).
    """

    if bool(proj_url) == all_projects:
        log.error('Use either --project or --all.')
        return 1

    from pillar.api.utils.authentication import force_cli_user
    force_cli_user()

    from pillar.api.node_types.asset import node_type_asset
    from pillar.api.node_types.page import node_type_page
    from pillar.api.node_types.post import node_type_post
    from pillar.api.node_types import attachments_embedded_schema
    from pillar.api.utils import remove_private_keys

    # Node types that support attachments
    node_types = (node_type_asset, node_type_page, node_type_post)
    nts_by_name = {nt['name']: nt for nt in node_types}

    db = current_app.db()
    projects_coll = db['projects']
    nodes_coll = db['nodes']

    def handle_project(project):
        log.info('Handling project %s', project['url'])

        replace_schemas(project)
        replace_attachments(project)

    def replace_schemas(project):
        for proj_nt in project['node_types']:
            nt_name = proj_nt['name']
            if nt_name not in nts_by_name:
                continue

            log.info('   - replacing attachment schema on node type "%s"', nt_name)
            pillar_nt = nts_by_name[nt_name]
            proj_nt['dyn_schema']['attachments'] = copy.deepcopy(attachments_embedded_schema)

            # Get the form schema the same as the official Pillar one, but only for attachments.
            try:
                pillar_form_schema = pillar_nt['form_schema']['attachments']
            except KeyError:
                proj_nt['form_schema'].pop('attachments', None)
            else:
                proj_nt['form_schema']['attachments'] = pillar_form_schema

        # Use Eve to PUT, so we have schema checking.
        db_proj = remove_private_keys(project)
        r, _, _, status = current_app.put_internal('projects', db_proj, _id=project['_id'])
        if status != 200:
            log.error('Error %i storing altered project %s %s', status, project['_id'], r)
            raise SystemExit('Error storing project, see log.')
        log.info('Project saved succesfully.')

    def replace_attachments(project):
        log.info('Upgrading nodes for project %s', project['url'])
        nodes = nodes_coll.find({
            '_deleted': False,
            'project': project['_id'],
            'node_type': {'$in': list(nts_by_name)},
            'properties.attachments': {'$exists': True},
        })
        for node in nodes:
            attachments = node['properties']['attachments']
            if isinstance(attachments, dict):
                # This node has already been upgraded.
                continue

            log.info('    - Updating schema on node %s (%s)', node['_id'], node.get('name'))
            new_atts = {}
            for field_info in attachments:
                for attachment in field_info.get('files', []):
                    new_atts[attachment['slug']] = {'oid': attachment['file']}

            node['properties']['attachments'] = new_atts

            # Use Eve to PUT, so we have schema checking.
            db_node = remove_private_keys(node)
            r, _, _, status = current_app.put_internal('nodes', db_node, _id=node['_id'])
            if status != 200:
                log.error('Error %i storing altered node %s %s', status, node['_id'], r)
                raise SystemExit('Error storing node; see log.')

    if all_projects:
        for proj in projects_coll.find():
            handle_project(proj)
        return

    proj = projects_coll.find_one({'url': proj_url})
    if not proj:
        log.error('Project url=%s not found', proj_url)
        return 3

    handle_project(proj)


def _find_orphan_files(project_id: bson.ObjectId) -> typing.Set[bson.ObjectId]:
    """Finds all non-referenced files for the given project.

    Returns an iterable of all orphan file IDs.
    """

    log.debug('Finding orphan files for project %s', project_id)

    # Get all file IDs that belong to this project.
    files_coll = current_app.db('files')
    cursor = files_coll.find({'project': project_id}, projection={'_id': 1})
    file_ids = {doc['_id'] for doc in cursor}
    if not file_ids:
        log.debug('Project %s has no files', project_id)
        return set()

    total_file_count = len(file_ids)
    log.debug('Project %s has %d files in total', project_id, total_file_count)

    def find_object_ids(something: typing.Any) -> typing.Iterable[bson.ObjectId]:
        if isinstance(something, bson.ObjectId):
            yield something
        elif isinstance(something, (list, set, tuple)):
            for item in something:
                yield from find_object_ids(item)
        elif isinstance(something, dict):
            for item in something.values():
                yield from find_object_ids(item)

    # Find all references by iterating through the project itself and every document that has a
    # 'project' key set to this ObjectId.
    db = current_app.db()
    for coll_name in sorted(db.collection_names(include_system_collections=False)):
        if coll_name in ORPHAN_FINDER_SKIP_COLLECTIONS:
            continue

        doc_filter = {'_deleted': {'$ne': True}}
        if coll_name == 'projects':
            doc_filter['_id'] = project_id
        else:
            doc_filter['project'] = project_id

        log.debug('   - inspecting collection %r with filter %r', coll_name, doc_filter)
        coll = db[coll_name]
        for doc in coll.find(doc_filter):
            for obj_id in find_object_ids(doc):
                # Found an Object ID that is in use, so discard it from our set of file IDs.
                file_ids.discard(obj_id)

    orphan_count = len(file_ids)
    log.info('Project %s has %d files or which %d are orphaned (%d%%)',
             project_id, total_file_count, orphan_count, 100 * orphan_count / total_file_count)

    return file_ids


@manager_maintenance.command
@manager_maintenance.option('-p', '--project', dest='proj_url', nargs='?',
                            help='Project URL, use "all" to check all projects')
def find_orphan_files(proj_url):
    """Finds unused files in the given project.

    This is a heavy operation that inspects *everything* in MongoDB. Use with care.
    """
    from jinja2.filters import do_filesizeformat

    start_timestamp = datetime.datetime.now()

    projects_coll = current_app.db('projects')
    files_coll = current_app.db('files')

    if proj_url == 'all':
        log.warning('Iterating over ALL projects, may take a while')
        orphans = set()
        try:
            for project in projects_coll.find({'_deleted': {'$ne': True}}, projection={'_id': 1}):
                proj_orphans = _find_orphan_files(project['_id'])
                orphans.update(proj_orphans)
        except KeyboardInterrupt:
            log.warning('Keyboard interrupt received, stopping now '
                        'and showing intermediary results.')
    else:
        project = projects_coll.find_one({'url': proj_url}, projection={'_id': 1})
        if not project:
            log.error('Project url=%r not found', proj_url)
            return 1

        orphans = _find_orphan_files(project['_id'])

    if not orphans:
        log.info('No orphan files found, congratulations.')
        return 0

    aggr = files_coll.aggregate([
        {'$match': {'_id': {'$in': list(orphans)}}},
        {'$group': {
            '_id': None,
            'size': {'$sum': '$length_aggregate_in_bytes'},
        }}
    ])

    total_size = list(aggr)[0]['size']
    log.info('Total orphan file size: %s', do_filesizeformat(total_size, binary=True))
    if proj_url == 'all':
        orphan_count = len(orphans)
        total_count = files_coll.count()
        log.info('Total nr of orphan files: %d', orphan_count)
        log.info('Total nr of files       : %d', total_count)
        log.info('Orphan percentage       : %d%%', 100 * orphan_count / total_count)

    end_timestamp = datetime.datetime.now()
    duration = end_timestamp - start_timestamp
    log.info('Finding orphans took %s', duration)

    log.info('Writing Object IDs to orphan-files.txt')
    with open('orphan-files.txt', 'w') as outfile:
        outfile.write('\n'.join(str(oid) for oid in sorted(orphans)) + '\n')
