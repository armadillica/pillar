import copy
import datetime
import logging
from pathlib import PurePosixPath
import re
import typing

import bson.tz_util
from bson import ObjectId
from bson.errors import InvalidId
from flask_script import Manager
import pymongo

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


def _single_logger(*args, level=logging.INFO, **kwargs):
    """Construct a logger function that's only logging once."""

    shown = False

    def log_once():
        nonlocal shown
        if shown:
            return
        log.log(level, *args, **kwargs)
        shown = True

    return log_once


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
        pid = proj['_id']
        try:
            admin_group_perms = proj['permissions']['groups'][0]
        except IndexError:
            log.error('Project %s has no admin group', pid)
            return 255
        except KeyError:
            log.error('Project %s has no group permissions at all', pid)
            return 255

        user = users_coll.find_one({'_id': proj['user']},
                                   projection={'groups': 1})
        if user is None:
            log.error('Project %s has non-existing owner %s', pid, proj['user'])
            return 255

        user_groups = set(user['groups'])
        admin_group_id = admin_group_perms['group']
        if admin_group_id in user_groups:
            # All is fine!
            good += 1
            continue

        log.warning('User %s has no admin rights to home project %s -- needs group %s',
                    proj['user'], pid, admin_group_id)
        bad += 1

    log.info('%i projects OK, %i projects in error', good, bad)
    return bad


@manager_maintenance.option('-g', '--go', dest='go',
                            action='store_true', default=False,
                            help='Actually go and perform the changes, without this just '
                                 'shows differences.')
def purge_home_projects(go=False):
    """Deletes all home projects that have no owner."""
    from pillar.api.utils.authentication import force_cli_user
    force_cli_user()

    users_coll = current_app.data.driver.db['users']
    proj_coll = current_app.data.driver.db['projects']
    good = bad = 0

    def bad_projects():
        nonlocal good, bad

        for proj in proj_coll.find({'category': 'home', '_deleted': {'$ne': True}}):
            pid = proj['_id']
            uid = proj.get('user')
            if not uid:
                log.info('Project %s has no user assigned', uid)
                bad += 1
                yield pid
                continue

            if users_coll.find({'_id': uid, '_deleted': {'$ne': True}}).count() == 0:
                log.info('Project %s has non-existing owner %s', pid, uid)
                bad += 1
                yield pid
                continue

            good += 1

    if not go:
        log.info('Dry run, use --go to actually perform the changes.')

    for project_id in bad_projects():
        log.info('Soft-deleting project %s', project_id)
        if go:
            r, _, _, status = current_app.delete_internal('projects', _id=project_id)
            if status != 204:
                raise ValueError(f'Error {status} deleting {project_id}: {r}')

    log.info('%i projects OK, %i projects deleted', good, bad)
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

    loglevel = logging.WARNING if quiet else logging.DEBUG
    logging.getLogger('pillar.api.file_storage').setLevel(loglevel)

    # CLI parameters are passed as strings
    chunk_size = int(chunk_size)
    window = int(window)

    from pillar.api import file_storage

    file_storage.refresh_links_for_backend(backend_name, chunk_size, window * 3600)


@manager_maintenance.command
@manager_maintenance.option('-c', '--chunk', dest='chunk_size', default=50,
                            help='Number of links to update, use 0 to update all.')
def refresh_backend_links_celery(backend_name, chunk_size=50):
    """Starts a Celery task that refreshes all file links that are using a certain storage backend.
    """
    from pillar.celery import file_link_tasks

    chunk_size = int(chunk_size)  # CLI parameters are passed as strings
    file_link_tasks.regenerate_all_expired_links.delay(backend_name, chunk_size)

    log.info('File link regeneration task has been queued for execution.')


_var_type_re = re.compile(r'-[a-z0-9A-Z]+$')


def _fix_variation(fdoc, variation, nice_name):
    from pillar.api.file_storage_backends import Bucket

    # See if we can reuse the bucket we already had.
    backend = fdoc['backend']
    pid_str = str(fdoc['project'])
    bucket_cls = Bucket.for_backend(backend)
    bucket = bucket_cls(pid_str)

    var_path = PurePosixPath(variation["file_path"])
    # NOTE: this breaks for variations with double extensions
    var_stem = var_path.stem
    m = _var_type_re.search(var_stem)
    var_type = m.group(0) if m else ''
    var_name = f'{nice_name}{var_type}{var_path.suffix}'
    log.info(f'    - %s → %s', variation["file_path"], var_name)

    blob = bucket.blob(variation['file_path'])
    if not blob.exists():
        log.warning('Blob %s does not exist', blob)
        return

    try:
        blob.update_filename(var_name)
    except Exception:
        log.warning('Unable to update blob %s filename to %r', blob, var_name, exc_info=True)


@manager_maintenance.option('-p', '--project', dest='proj_url', nargs='?',
                            help='Project URL')
@manager_maintenance.option('-a', '--all', dest='all_projects', action='store_true', default=False,
                            help='Replace on all projects.')
@manager_maintenance.option('-c', '--chunk', dest='chunk_size', default=50,
                            help='Number of links to update, use 0 to update all.')
def refresh_content_disposition(proj_url=None, all_projects=False, chunk_size=0):
    """Refreshes the filename as mentioned in the Content Disposition header.

    Works on all files of a specific project, or on all files in general.
    Only works on variations, as this is intended to fix the database after
    T51477 is fixed, and that issue doesn't affect the original files.
    """
    from concurrent.futures import ProcessPoolExecutor as Executor

    if bool(proj_url) == all_projects:
        log.error('Use either --project or --all.')
        return 1

    # CLI parameters are passed as strings
    chunk_size = int(chunk_size)

    # Main implementation in separate function so that we're sure that
    # fix_variation() doesn't accidentally use nonlocal variables.
    def go():
        query = {'_deleted': {'$ne': False}}
        if proj_url:
            from pillar.api.projects.utils import get_project
            proj = get_project(proj_url)
            query['project'] = proj['_id']

        files_coll = current_app.db('files')
        cursor = files_coll.find(query)
        if all_projects:
            cursor = cursor.sort([('project', pymongo.ASCENDING)])
        cursor = cursor.limit(chunk_size)

        with Executor(max_workers=15) as exe:
            futures = []
            for fdoc in cursor:
                nice_name = PurePosixPath(fdoc['filename']).stem

                variations = fdoc.get('variations') or []
                futures.extend(exe.submit(_fix_variation, fdoc, variation, nice_name)
                               for variation in variations)
            for future in futures:
                future.result()

    go()


@manager_maintenance.command
def expire_all_project_links(project_uuid):
    """Expires all file links for a certain project without refreshing.

    This is just for testing.
    """

    import datetime
    from pillar.api.utils import utcnow

    files_collection = current_app.data.driver.db['files']

    expires = utcnow() - datetime.timedelta(days=1)
    result = files_collection.update_many(
        {'project': ObjectId(project_uuid)},
        {'$set': {'link_expires': expires}}
    )

    print('Expired %i links' % result.matched_count)


@manager_maintenance.option('-u', '--url', dest='project_url', nargs='?',
                            help='Project URL')
@manager_maintenance.option('-a', '--all', dest='all_projects', action='store_true', default=False,
                            help='Replace on all projects.')
@manager_maintenance.option('-m', '--missing', dest='missing',
                            action='store_true', default=False,
                            help='Add missing node types. Note that this may add unwanted ones.')
@manager_maintenance.option('-g', '--go', dest='go',
                            action='store_true', default=False,
                            help='Actually go and perform the changes, without this just '
                                 'shows differences.')
@manager_maintenance.option('-i', '--id', dest='project_id', nargs='?',
                            help='Project ID')
def replace_pillar_node_type_schemas(project_url=None, all_projects=False, missing=False, go=False,
                                     project_id=None):
    """Replaces the project's node type schemas with the standard Pillar ones.

    Non-standard node types are left alone.
    """

    from pillar.api.utils.authentication import force_cli_user
    force_cli_user()

    from pillar.api.node_types import PILLAR_NAMED_NODE_TYPES
    from pillar.api.utils import remove_private_keys, doc_diff

    will_would = 'Will' if go else 'Would'
    projects_changed = projects_seen = 0
    for proj in _db_projects(project_url, all_projects, project_id, go=go):
        projects_seen += 1

        orig_proj = copy.deepcopy(proj)
        proj_id = proj['_id']
        if 'url' not in proj:
            log.warning('Project %s has no URL!', proj_id)
        proj_url = proj.get('url', f'-no URL id {proj_id}')
        log.debug('Handling project %s', proj_url)

        for proj_nt in proj['node_types']:
            nt_name = proj_nt['name']
            try:
                pillar_nt = PILLAR_NAMED_NODE_TYPES[nt_name]
            except KeyError:
                log.debug('   - skipping non-standard node type "%s"', nt_name)
                continue

            log.debug('   - replacing schema on node type "%s"', nt_name)

            # This leaves node type keys intact that aren't in Pillar's node_type_xxx definitions,
            # such as permissions. It also keeps form schemas as-is.
            pillar_nt.pop('form_schema', None)
            proj_nt.update(copy.deepcopy(pillar_nt))

        # Find new node types that aren't in the project yet.
        if missing:
            project_ntnames = set(nt['name'] for nt in proj['node_types'])
            for nt_name in set(PILLAR_NAMED_NODE_TYPES.keys()) - project_ntnames:
                log.info('   - Adding node type "%s"', nt_name)
                pillar_nt = PILLAR_NAMED_NODE_TYPES[nt_name]
                proj['node_types'].append(copy.deepcopy(pillar_nt))

        proj_has_difference = False
        for key, val1, val2 in doc_diff(orig_proj, proj, falsey_is_equal=False):
            if not proj_has_difference:
                if proj.get('_deleted', False):
                    deleted = ' (deleted)'
                else:
                    deleted = ''
                log.info('%s change project %s%s', will_would, proj_url, deleted)
                proj_has_difference = True
            log.info('    %30r: %r → %r', key, val1, val2)

        projects_changed += proj_has_difference

        if go and proj_has_difference:
            # Use Eve to PUT, so we have schema checking.
            db_proj = remove_private_keys(proj)
            try:
                r, _, _, status = current_app.put_internal('projects', db_proj, _id=proj_id)
            except Exception:
                log.exception('Error saving project %s (url=%s)', proj_id, proj_url)
                raise SystemExit(5)

            if status != 200:
                log.error('Error %i storing altered project %s %s', status, proj['_id'], r)
                raise SystemExit('Error storing project, see log.')
            log.debug('Project saved succesfully.')

    log.info('%s %d of %d projects',
             'Changed' if go else 'Would change',
             projects_changed, projects_seen)


@manager_maintenance.option('-p', '--project', dest='proj_url', nargs='?',
                            help='Project URL')
@manager_maintenance.option('-a', '--all', dest='all_projects', action='store_true', default=False,
                            help='Replace on all projects.')
@manager_maintenance.option('-g', '--go', dest='go', action='store_true', default=False,
                            help='Actually perform the changes (otherwise just show as dry-run).')
def upgrade_attachment_schema(proj_url=None, all_projects=False, go=False):
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
    from pillar.api.utils import remove_private_keys, doc_diff

    # Node types that support attachments
    node_types = (node_type_asset, node_type_page, node_type_post)
    nts_by_name = {nt['name']: nt for nt in node_types}

    nodes_coll = current_app.db('nodes')

    def replace_schemas(project):
        project_url = project.get('url', '-no-url-')
        log_proj = _single_logger('Upgrading schema project %s (%s)', project_url, project['_id'])

        orig_proj = copy.deepcopy(project)
        for proj_nt in project['node_types']:
            nt_name = proj_nt['name']
            if nt_name not in nts_by_name:
                continue

            pillar_nt = nts_by_name[nt_name]
            pillar_dyn_schema = pillar_nt['dyn_schema']
            if proj_nt['dyn_schema'] == pillar_dyn_schema:
                # Schema already up to date.
                continue

            log_proj()
            log.info('   - replacing dyn_schema on node type "%s"', nt_name)
            proj_nt['dyn_schema'] = copy.deepcopy(pillar_dyn_schema)

        seen_changes = False
        for key, val1, val2 in doc_diff(orig_proj, project):
            if not seen_changes:
                log.info('Schema changes to project %s (%s):', project_url, project['_id'])
                seen_changes = True
            log.info('    - %30s: %s → %s', key, val1, val2)

        if go:
            # Use Eve to PUT, so we have schema checking.
            db_proj = remove_private_keys(project)
            r, _, _, status = current_app.put_internal('projects', db_proj, _id=project['_id'])
            if status != 200:
                log.error('Error %i storing altered project %s %s', status, project['_id'], r)
                raise SystemExit('Error storing project, see log.')
            log.debug('Project saved succesfully.')

    def replace_attachments(project):
        project_url = project.get('url', '-no-url-')
        log_proj = _single_logger('Upgrading nodes for project %s (%s)',
                                  project_url, project['_id'])

        # Remove empty attachments
        if go:
            res = nodes_coll.update_many(
                {'properties.attachments': {},
                 'project': project['_id']},
                {'$unset': {'properties.attachments': 1}},
            )
            if res.matched_count > 0:
                log_proj()
                log.info('Removed %d empty attachment dicts', res.modified_count)
        else:
            to_remove = nodes_coll.count_documents({'properties.attachments': {},
                                                    'project': project['_id']})
            if to_remove:
                log_proj()
                log.info('Would remove %d empty attachment dicts', to_remove)

        # Convert attachments.
        nodes = nodes_coll.find({
            '_deleted': False,
            'project': project['_id'],
            'node_type': {'$in': list(nts_by_name)},
            'properties.attachments': {'$exists': True},
        })
        for node in nodes:
            attachments = node['properties']['attachments']
            if not attachments:
                # If we're not modifying the database (e.g. go=False),
                # any attachments={} will not be filtered out earlier.
                if go or attachments != {}:
                    log_proj()
                    log.info('    - Node %s (%s) still has empty attachments %r',
                             node['_id'], node.get('name'), attachments)
                continue

            if isinstance(attachments, dict):
                # This node has already been upgraded.
                continue

            # Upgrade from list [{'slug': 'xxx', 'oid': 'yyy'}, ...]
            # to dict {'xxx': {'oid': 'yyy'}, ...}
            log_proj()
            log.info('    - Updating schema on node %s (%s)', node['_id'], node.get('name'))
            new_atts = {}
            for field_info in attachments:
                for attachment in field_info.get('files', []):
                    new_atts[attachment['slug']] = {'oid': attachment['file']}

            node['properties']['attachments'] = new_atts
            log.info('      from %s to %s', attachments, new_atts)

            if go:
                # Use Eve to PUT, so we have schema checking.
                db_node = remove_private_keys(node)
                r, _, _, status = current_app.put_internal('nodes', db_node, _id=node['_id'])
                if status != 200:
                    log.error('Error %i storing altered node %s %s', status, node['_id'], r)
                    raise SystemExit('Error storing node; see log.')

    for proj in _db_projects(proj_url, all_projects, go=go):
        replace_schemas(proj)
        replace_attachments(proj)


def iter_markdown(proj_node_types: dict, some_node: dict, callback: typing.Callable[[str], str]):
    """Calls the callback for each MarkDown value in the node.

    Replaces the value in-place with the return value of the callback.
    """
    from collections import deque
    from pillar.api.eve_settings import nodes_schema

    my_log = log.getChild('iter_markdown')

    # Inspect the node type to find properties containing Markdown.
    node_type_name = some_node['node_type']
    try:
        node_type = proj_node_types[node_type_name]
    except KeyError:
        raise KeyError(f'Project has no node type {node_type_name}')

    to_visit = deque([
        (some_node, nodes_schema),
        (some_node['properties'], node_type['dyn_schema'])])
    while to_visit:
        doc, doc_schema = to_visit.popleft()
        for key, definition in doc_schema.items():
            if definition.get('type') == 'dict' and definition.get('schema'):
                # This is a subdocument with its own schema, visit it later.
                subdoc = doc.get(key)
                if not subdoc:
                    continue
                to_visit.append((subdoc, definition['schema']))
                continue
            coerce = definition.get('coerce')  # Eve < 0.8
            validator = definition.get('validator')  # Eve >= 0.8
            if coerce != 'markdown' and validator != 'markdown':
                continue

            my_log.debug('I have to change %r of %s', key, doc)
            old_value = doc.get(key)
            if not old_value:
                continue
            new_value = callback(old_value)
            doc[key] = new_value


@manager_maintenance.option('-p', '--project', dest='proj_url', nargs='?',
                            help='Project URL')
@manager_maintenance.option('-a', '--all', dest='all_projects', action='store_true', default=False,
                            help='Replace on all projects.')
@manager_maintenance.option('-g', '--go', dest='go', action='store_true', default=False,
                            help='Actually perform the changes (otherwise just show as dry-run).')
def upgrade_attachment_usage(proj_url=None, all_projects=False, go=False):
    """Replaces '@[slug]' with '{attachment slug}'.

    Also moves links from the attachment dict to the attachment shortcode.
    """
    if bool(proj_url) == all_projects:
        log.error('Use either --project or --all.')
        return 1

    import html
    from pillar.api.projects.utils import node_type_dict
    from pillar.api.utils import remove_private_keys
    from pillar.api.utils.authentication import force_cli_user

    force_cli_user()

    nodes_coll = current_app.db('nodes')
    total_nodes = 0
    failed_node_ids = set()

    # Use a mixture of the old slug RE that still allowes spaces in the slug
    # name and the new RE that allows dashes.
    old_slug_re = re.compile(r'@\[([a-zA-Z0-9_\- ]+)\]')
    for proj in _db_projects(proj_url, all_projects, go=go):
        proj_id = proj['_id']
        proj_url = proj.get('url', '-no-url-')
        nodes = nodes_coll.find({
            '_deleted': {'$ne': True},
            'project': proj_id,
            'properties.attachments': {'$exists': True},
        })
        node_count = nodes.count()
        if node_count == 0:
            log.debug('Skipping project %s (%s)', proj_url, proj_id)
            continue

        proj_node_types = node_type_dict(proj)

        for node in nodes:
            attachments = node['properties']['attachments']
            replaced = False

            # Inner functions because of access to the node's attachments.
            def replace(match):
                nonlocal replaced
                slug = match.group(1)
                log.debug('    - OLD STYLE attachment slug %r', slug)
                try:
                    att = attachments[slug]
                except KeyError:
                    log.info("Attachment %r not found for node %s", slug, node['_id'])
                    link = ''
                else:
                    link = att.get('link', '')
                    if link == 'self':
                        link = " link='self'"
                    elif link == 'custom':
                        url = att.get('link_custom')
                        if url:
                            link = " link='%s'" % html.escape(url)
                replaced = True
                return '{attachment %r%s}' % (slug.replace(' ', '-'), link)

            def update_markdown(value: str) -> str:
                return old_slug_re.sub(replace, value)

            iter_markdown(proj_node_types, node, update_markdown)

            # Remove no longer used properties from attachments
            new_attachments = {}
            for slug, attachment in attachments.items():
                replaced |= 'link' in attachment  # link_custom implies link
                attachment.pop('link', None)
                attachment.pop('link_custom', None)
                new_attachments[slug.replace(' ', '-')] = attachment
            node['properties']['attachments'] = new_attachments

            if replaced:
                total_nodes += 1
            else:
                # Nothing got replaced,
                continue

            if go:
                # Use Eve to PUT, so we have schema checking.
                db_node = remove_private_keys(node)
                r, _, _, status = current_app.put_internal('nodes', db_node, _id=node['_id'])
                if status != 200:
                    log.error('Error %i storing altered node %s %s', status, node['_id'], r)
                    failed_node_ids.add(node['_id'])
                    # raise SystemExit('Error storing node; see log.')
                log.debug('Updated node %s: %s', node['_id'], r)

        log.info('Project %s (%s) has %d nodes with attachments',
                 proj_url, proj_id, node_count)
    log.info('%s %d nodes', 'Updated' if go else 'Would update', total_nodes)
    if failed_node_ids:
        log.warning('Failed to update %d of %d nodes: %s', len(failed_node_ids), total_nodes,
                    ', '.join(str(nid) for nid in failed_node_ids))


def _db_projects(proj_url: str, all_projects: bool, project_id='', *, go: bool) \
        -> typing.Iterable[dict]:
    """Yields a subset of the projects in the database.

    :param all_projects: when True, yields all projects.
    :param proj_url: when all_projects is False, this denotes the project
        to yield.

    Handles soft-deleted projects as non-existing. This ensures that
    the receiver can actually modify and save the project without any
    issues.

    Also shows duration and a note about dry-running when go=False.
    """
    if sum([bool(proj_url), all_projects, bool(project_id)]) != 1:
        log.error('Only use one way to specify a project / all projects')
        raise SystemExit(1)

    projects_coll = current_app.db('projects')
    start = datetime.datetime.now()
    if all_projects:
        yield from projects_coll.find({'_deleted': {'$ne': True}})
    else:
        if proj_url:
            q = {'url': proj_url}
        else:
            q = {'_id': bson.ObjectId(project_id)}
        proj = projects_coll.find_one({**q, '_deleted': {'$ne': True}})
        if not proj:
            log.error('Project %s not found', q)
            raise SystemExit(3)
        yield proj

    if not go:
        log.info('Dry run, use --go to perform the change.')
    duration = datetime.datetime.now() - start
    log.info('Command took %s', duration)


def _find_orphan_files() -> typing.Set[bson.ObjectId]:
    """Finds all non-referenced files for the given project.

    Returns an iterable of all orphan file IDs.
    """
    log.debug('Finding orphan files')

    # Get all file IDs that belong to this project.
    files_coll = current_app.db('files')
    cursor = files_coll.find({'_deleted': {'$ne': True}}, projection={'_id': 1})
    file_ids = {doc['_id'] for doc in cursor}
    if not file_ids:
        log.debug('No files found')
        return set()

    total_file_count = len(file_ids)
    log.debug('Found %d files in total', total_file_count)

    def find_object_ids(something: typing.Any) -> typing.Iterable[bson.ObjectId]:
        if isinstance(something, bson.ObjectId):
            yield something
        elif isinstance(something, str) and len(something) == 24:
            try:
                yield bson.ObjectId(something)
            except (bson.objectid.InvalidId, TypeError):
                # It apparently wasn't an ObjectID after all.
                pass
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
        log.debug('   - inspecting collection %r with filter %r', coll_name, doc_filter)
        coll = db[coll_name]
        for doc in coll.find(doc_filter):
            for obj_id in find_object_ids(doc):
                # Found an Object ID that is in use, so discard it from our set of file IDs.
                file_ids.discard(obj_id)

    orphan_count = len(file_ids)
    log.info('Found %d files or which %d are orphaned (%d%%)',
             total_file_count, orphan_count, 100 * orphan_count / total_file_count)

    return file_ids


@manager_maintenance.command
def find_orphan_files():
    """Finds unused files in the given project.

    This is a heavy operation that inspects *everything* in MongoDB. Use with care.
    """
    from jinja2.filters import do_filesizeformat
    from pathlib import Path

    output_fpath = Path(current_app.config['STORAGE_DIR']) / 'orphan-files.txt'
    if output_fpath.exists():
        log.error('Output filename %s already exists, remove it first.', output_fpath)
        return 1

    start_timestamp = datetime.datetime.now()
    orphans = _find_orphan_files()
    if not orphans:
        log.info('No orphan files found, congratulations.')
        return 0

    files_coll = current_app.db('files')
    aggr = files_coll.aggregate([
        {'$match': {'_id': {'$in': list(orphans)}}},
        {'$group': {
            '_id': None,
            'size': {'$sum': '$length_aggregate_in_bytes'},
        }}
    ])

    total_size = list(aggr)[0]['size']
    log.info('Total orphan file size: %s', do_filesizeformat(total_size, binary=True))
    orphan_count = len(orphans)
    total_count = files_coll.count()
    log.info('Total nr of orphan files: %d', orphan_count)
    log.info('Total nr of files       : %d', total_count)
    log.info('Orphan percentage       : %d%%', 100 * orphan_count / total_count)

    end_timestamp = datetime.datetime.now()
    duration = end_timestamp - start_timestamp
    log.info('Finding orphans took %s', duration)

    log.info('Writing Object IDs to %s', output_fpath)
    with output_fpath.open('w', encoding='ascii') as outfile:
        outfile.write('\n'.join(str(oid) for oid in sorted(orphans)) + '\n')


@manager_maintenance.command
def delete_orphan_files():
    """Deletes orphan files mentioned in orphan-files.txt

    Use 'find_orphan_files' first to generate orphan-files.txt.
    """
    import pymongo.results
    from pathlib import Path

    output_fpath = Path(current_app.config['STORAGE_DIR']) / 'orphan-files.txt'
    with output_fpath.open('r', encoding='ascii') as infile:
        oids = [bson.ObjectId(oid.strip()) for oid in infile]

    log.info('Found %d Object IDs to remove', len(oids))

    # Ensure that the list of Object IDs actually matches files.
    # I hope this works as a security measure against deleting from obsolete orphan-files.txt files.
    files_coll = current_app.db('files')
    oid_filter = {'_id': {'$in': oids},
                  '_deleted': {'$ne': True}}
    file_count = files_coll.count(oid_filter)
    if file_count == len(oids):
        log.info('Found %d matching files', file_count)
    else:
        log.warning("Found %d matching files, which doesn't match the number of Object IDs. "
                    "Refusing to continue.", file_count)
        return 1

    res: pymongo.results.UpdateResult = files_coll.update_many(
        oid_filter,
        {'$set': {'_deleted': True}}
    )
    if res.matched_count != file_count:
        log.warning('Soft-deletion matched %d of %d files', res.matched_count, file_count)
    elif res.modified_count != file_count:
        log.warning('Soft-deletion modified %d of %d files', res.modified_count, file_count)

    log.info('%d files have been soft-deleted', res.modified_count)


@manager_maintenance.command
def find_video_files_without_duration():
    """Finds video files without any duration

    This is a heavy operation. Use with care.
    """
    from pathlib import Path

    output_fpath = Path(current_app.config['STORAGE_DIR']) / 'video_files_without_duration.txt'
    if output_fpath.exists():
        log.error('Output filename %s already exists, remove it first.', output_fpath)
        return 1

    start_timestamp = datetime.datetime.now()
    files_coll = current_app.db('files')
    starts_with_video = re.compile("^video", re.IGNORECASE)
    aggr = files_coll.aggregate([
        {'$match': {'content_type': starts_with_video,
                    '_deleted': {'$ne': True}}},
        {'$unwind': '$variations'},
        {'$match': {
            'variations.duration': {'$not': {'$gt': 0}}
        }},
        {'$project': {'_id': 1}}
    ])

    file_ids = [str(f['_id']) for f in aggr]
    nbr_files = len(file_ids)
    log.info('Total nbr video files without duration: %d', nbr_files)

    end_timestamp = datetime.datetime.now()
    duration = end_timestamp - start_timestamp
    log.info('Finding files took %s', duration)

    log.info('Writing Object IDs to %s', output_fpath)
    with output_fpath.open('w', encoding='ascii') as outfile:
        outfile.write('\n'.join(sorted(file_ids)))

@manager_maintenance.command
def find_video_nodes_without_duration():
    """Finds video nodes without any duration

    This is a heavy operation. Use with care.
    """
    from pathlib import Path

    output_fpath = Path(current_app.config['STORAGE_DIR']) / 'video_nodes_without_duration.txt'
    if output_fpath.exists():
        log.error('Output filename %s already exists, remove it first.', output_fpath)
        return 1

    start_timestamp = datetime.datetime.now()
    nodes_coll = current_app.db('nodes')

    aggr = nodes_coll.aggregate([
        {'$match': {'node_type': 'asset',
                    'properties.content_type': 'video',
                    '_deleted': {'$ne': True},
                    'properties.duration_seconds': {'$not': {'$gt': 0}}}},
        {'$project': {'_id': 1}}
    ])

    file_ids = [str(f['_id']) for f in aggr]
    nbr_files = len(file_ids)
    log.info('Total nbr video nodes without duration: %d', nbr_files)

    end_timestamp = datetime.datetime.now()
    duration = end_timestamp - start_timestamp
    log.info('Finding nodes took %s', duration)

    log.info('Writing Object IDs to %s', output_fpath)
    with output_fpath.open('w', encoding='ascii') as outfile:
        outfile.write('\n'.join(sorted(file_ids)))


@manager_maintenance.option('-n', '--nodes', dest='nodes_to_update', nargs='*',
                            help='List of nodes to update')
@manager_maintenance.option('-a', '--all', dest='all_nodes', action='store_true', default=False,
                            help='Update on all video nodes.')
@manager_maintenance.option('-g', '--go', dest='go', action='store_true', default=False,
                            help='Actually perform the changes (otherwise just show as dry-run).')
def reconcile_node_video_duration(nodes_to_update=None, all_nodes=False, go=False):
    """Copy video duration from file.variations.duration to node.properties.duraion_seconds

    This is a heavy operation. Use with care.
    """
    from pillar.api.utils import random_etag, utcnow

    if bool(nodes_to_update) == all_nodes:
        log.error('Use either --nodes or --all.')
        return 1

    start_timestamp = datetime.datetime.now()

    nodes_coll = current_app.db('nodes')
    node_subset = []
    if nodes_to_update:
        node_subset = [{'$match': {'_id': {'$in': [ObjectId(nid) for nid in nodes_to_update]}}}]
    files = nodes_coll.aggregate(
        [
            *node_subset,
            {'$match': {
                'node_type': 'asset',
                'properties.content_type': 'video',
                '_deleted': {'$ne': True}}
            },
            {'$lookup': {
                'from': 'files',
                'localField': 'properties.file',
                'foreignField': '_id',
                'as': '_files',
            }},
            {'$unwind': '$_files'},
            {'$unwind': '$_files.variations'},
            {'$match': {'_files.variations.duration': {'$gt': 0}}},
            {'$addFields': {
                'need_update': {'$ne': ['$_files.variations.duration', '$properties.duration_seconds']}
            }},
            {'$match': {'need_update': True}},
            {'$project': {
                '_id': 1,
                'duration': '$_files.variations.duration',
            }}]
    )

    if not go:
        log.info('Would try to update %d nodes', len(list(files)))
        return 0

    modified_count = 0
    for f in files:
        log.debug('Updating node %s with duration %d', f['_id'], f['duration'])
        new_etag = random_etag()
        now = utcnow()
        resp = nodes_coll.update_one(
            {'_id': f['_id']},
            {'$set': {
                'properties.duration_seconds': f['duration'],
                '_etag': new_etag,
                '_updated': now,
            }}
        )
        if resp.modified_count == 0:
            log.debug('Node %s was already up to date', f['_id'])
        modified_count += resp.modified_count

    log.info('Updated %d nodes', modified_count)
    end_timestamp = datetime.datetime.now()
    duration = end_timestamp - start_timestamp
    log.info('Operation took %s', duration)
    return 0
