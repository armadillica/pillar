"""Commandline interface.

Run commands with 'flask <command>'
"""

from __future__ import print_function, division

import copy
import logging

from bson.objectid import ObjectId, InvalidId
from eve.methods.put import put_internal
from eve.methods.post import post_internal

from flask import current_app
from flask_script import Manager

log = logging.getLogger(__name__)
manager = Manager(current_app)


@manager.command
def setup_db(admin_email):
    """Setup the database
    - Create admin, subscriber and demo Group collection
    - Create admin user (must use valid blender-id credentials)
    - Create one project
    """

    # Create default groups
    groups_list = []
    for group in ['admin', 'subscriber', 'demo']:
        g = {'name': group}
        g = current_app.post_internal('groups', g)
        groups_list.append(g[0]['_id'])
        print("Creating group {0}".format(group))

    # Create admin user
    user = {'username': admin_email,
            'groups': groups_list,
            'roles': ['admin', 'subscriber', 'demo'],
            'settings': {'email_communications': 1},
            'auth': [],
            'full_name': admin_email,
            'email': admin_email}
    result, _, _, status = current_app.post_internal('users', user)
    if status != 201:
        raise SystemExit('Error creating user {}: {}'.format(admin_email, result))
    user.update(result)
    print("Created user {0}".format(user['_id']))

    # Create a default project by faking a POST request.
    with current_app.test_request_context(data={'project_name': u'Default Project'}):
        from flask import g
        from pillar.api.projects import routes as proj_routes

        g.current_user = {'user_id': user['_id'],
                          'groups': user['groups'],
                          'roles': set(user['roles'])}

        proj_routes.create_project(overrides={'url': 'default-project',
                                              'is_private': False})


@manager.command
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

    for blender_id, users in found_users.iteritems():
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


@manager.command
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


@manager.command
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


@manager.command
def badger(action, user_email, role):
    from pillar.api import service

    with current_app.app_context():
        service.fetch_role_to_group_id_map()
        response, status = service.do_badger(action, user_email, role)

    if status == 204:
        log.info('Done.')
    else:
        log.info('Response: %s', response)
        log.info('Status  : %i', status)


def create_service_account(email, service_roles, service_definition):
    from pillar.api import service
    from pillar.api.utils import dumps

    account, token = service.create_service_account(
        email,
        service_roles,
        service_definition
    )

    print('Account created:')
    print(dumps(account, indent=4, sort_keys=True))
    print()
    print('Access token: %s' % token['token'])
    print('  expires on: %s' % token['expire_time'])
    return account, token


@manager.command
def create_badger_account(email, badges):
    """
    Creates a new service account that can give badges (i.e. roles).

    :param email: email address associated with the account
    :param badges: single space-separated argument containing the roles
        this account can assign and revoke.
    """

    create_service_account(email, [u'badger'], {'badger': badges.strip().split()})


@manager.command
def create_urler_account(email):
    """Creates a new service account that can fetch all project URLs."""

    create_service_account(email, [u'urler'], {})


@manager.command
def create_local_user_account(email, password):
    from pillar.api.local_auth import create_local_user
    create_local_user(email, password)


@manager.command
@manager.option('-c', '--chunk', dest='chunk_size', default=50,
                help='Number of links to update, use 0 to update all.')
@manager.option('-q', '--quiet', dest='quiet', action='store_true', default=False)
@manager.option('-w', '--window', dest='window', default=12,
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


@manager.command
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


@manager.command
def check_cdnsun():
    import requests

    files_collection = current_app.data.driver.db['files']

    s = requests.session()

    missing_main = 0
    missing_variation = 0
    fdocs = files_collection.find({'backend': 'cdnsun'})
    for idx, fdoc in enumerate(fdocs):
        if idx % 100 == 0:
            print('Handling file %i/~1800' % (idx + 1))

        variations = fdoc.get('variations', ())
        resp = s.head(fdoc['link'])
        if resp.status_code == 404:
            missing_main += 1
            if variations:
                # print('File %(_id)s (%(filename)s): link not found, checking variations' % fdoc)
                pass
            else:
                print('File %(_id)s (%(filename)s): link not found, and no variations' % fdoc)

        for var in variations:
            resp = s.head(var['link'])
            if resp.status_code != 200:
                missing_variation += 1
                print('File %s (%s): error %i for variation %s' % (
                    fdoc['_id'], fdoc['filename'], resp.status_code, var['link']))

    print('Missing main: %i' % missing_main)
    print('Missing vars: %i' % missing_variation)


@manager.command
def file_change_backend(file_id, dest_backend='gcs'):
    """Given a file document, move it to the specified backend (if not already
    there) and update the document to reflect that.
    Files on the original backend are not deleted automatically.
    """

    from pillar.api.file_storage.moving import change_file_storage_backend
    change_file_storage_backend(file_id, dest_backend)


@manager.command
def mass_copy_between_backends(src_backend='cdnsun', dest_backend='gcs'):
    """Copies all files from one backend to the other, updating them in Mongo.

    Files on the original backend are not deleted.
    """

    import requests.exceptions

    from pillar.api.file_storage import moving

    logging.getLogger('pillar').setLevel(logging.INFO)
    log.info('Mass-moving all files from backend %r to %r',
             src_backend, dest_backend)

    files_coll = current_app.data.driver.db['files']

    fdocs = files_coll.find({'backend': src_backend},
                            projection={'_id': True})
    copied_ok = 0
    copy_errs = 0
    try:
        for fdoc in fdocs:
            try:
                moving.change_file_storage_backend(fdoc['_id'], dest_backend)
            except moving.PrerequisiteNotMetError as ex:
                log.error('Error copying %s: %s', fdoc['_id'], ex)
                copy_errs += 1
            except requests.exceptions.HTTPError as ex:
                log.error('Error copying %s (%s): %s',
                          fdoc['_id'], ex.response.url, ex)
                copy_errs += 1
            except Exception:
                log.exception('Unexpected exception handling file %s', fdoc['_id'])
                copy_errs += 1
            else:
                copied_ok += 1
    except KeyboardInterrupt:
        log.error('Stopping due to keyboard interrupt')

    log.info('%i files copied ok', copied_ok)
    log.info('%i files we did not copy', copy_errs)


@manager.command
@manager.option('-p', '--project', dest='dest_proj_url',
                help='Destination project URL')
@manager.option('-f', '--force', dest='force', action='store_true', default=False,
                help='Move even when already at the given project.')
@manager.option('-s', '--skip-gcs', dest='skip_gcs', action='store_true', default=False,
                help='Skip file handling on GCS, just update the database.')
def move_group_node_project(node_uuid, dest_proj_url, force=False, skip_gcs=False):
    """Copies all files from one project to the other, then moves the nodes.

    The node and all its children are moved recursively.
    """

    from pillar.api.nodes import moving
    from pillar.api.utils import str2id

    logging.getLogger('pillar').setLevel(logging.INFO)

    db = current_app.db()
    nodes_coll = db['nodes']
    projs_coll = db['projects']

    # Parse CLI args and get the node, source and destination projects.
    node_uuid = str2id(node_uuid)
    node = nodes_coll.find_one({'_id': node_uuid})
    if node is None:
        log.error("Node %s can't be found!", node_uuid)
        return 1

    if node.get('parent', None):
        log.error('Node cannot have a parent, it must be top-level.')
        return 4

    src_proj = projs_coll.find_one({'_id': node['project']})
    dest_proj = projs_coll.find_one({'url': dest_proj_url})

    if src_proj is None:
        log.warning("Node's source project %s doesn't exist!", node['project'])
    if dest_proj is None:
        log.error("Destination project url='%s' doesn't exist.", dest_proj_url)
        return 2
    if src_proj['_id'] == dest_proj['_id']:
        if force:
            log.warning("Node is already at project url='%s'!", dest_proj_url)
        else:
            log.error("Node is already at project url='%s'!", dest_proj_url)
            return 3

    log.info("Mass-moving %s (%s) and children from project '%s' (%s) to '%s' (%s)",
             node_uuid, node['name'], src_proj['url'], src_proj['_id'], dest_proj['url'],
             dest_proj['_id'])

    mover = moving.NodeMover(db=db, skip_gcs=skip_gcs)
    mover.change_project(node, dest_proj)

    log.info('Done moving.')


@manager.command
@manager.option('-p', '--project', dest='proj_url', nargs='?',
                help='Project URL')
@manager.option('-a', '--all', dest='all_projects', action='store_true', default=False,
                help='Replace on all projects.')
def replace_pillar_node_type_schemas(proj_url=None, all_projects=False):
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

        # Use Eve to PUT, so we have schema checking.
        db_proj = remove_private_keys(project)
        r, _, _, status = put_internal('projects', db_proj, _id=project['_id'])
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


@manager.command
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


@manager.command
@manager.option('-p', '--project', dest='proj_url', nargs='?',
                help='Project URL')
@manager.option('-a', '--all', dest='all_projects', action='store_true', default=False,
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
    from pillar.api.node_types import _attachments_embedded_schema
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
            proj_nt['dyn_schema']['attachments'] = copy.deepcopy(_attachments_embedded_schema)

            # Get the form schema the same as the official Pillar one, but only for attachments.
            try:
                pillar_form_schema = pillar_nt['form_schema']['attachments']
            except KeyError:
                proj_nt['form_schema'].pop('attachments', None)
            else:
                proj_nt['form_schema']['attachments'] = pillar_form_schema

        # Use Eve to PUT, so we have schema checking.
        db_proj = remove_private_keys(project)
        r, _, _, status = put_internal('projects', db_proj, _id=project['_id'])
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
            attachments = node[u'properties'][u'attachments']
            if isinstance(attachments, dict):
                # This node has already been upgraded.
                continue

            log.info('    - Updating schema on node %s (%s)', node['_id'], node.get('name'))
            new_atts = {}
            for field_info in attachments:
                for attachment in field_info.get('files', []):
                    new_atts[attachment[u'slug']] = {u'oid': attachment[u'file']}

            node[u'properties'][u'attachments'] = new_atts

            # Use Eve to PUT, so we have schema checking.
            db_node = remove_private_keys(node)
            r, _, _, status = put_internal('nodes', db_node, _id=node['_id'])
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


@manager.command
def create_blog(proj_url):
    """Adds a blog to the project."""

    from pillar.api.utils.authentication import force_cli_user
    from pillar.api.utils import node_type_utils
    from pillar.api.node_types.blog import node_type_blog
    from pillar.api.node_types.post import node_type_post
    from pillar.api.utils import remove_private_keys

    force_cli_user()

    db = current_app.db()

    # Add the blog & post node types to the project.
    projects_coll = db['projects']
    proj = projects_coll.find_one({'url': proj_url})
    if not proj:
        log.error('Project url=%s not found', proj_url)
        return 3

    node_type_utils.add_to_project(proj,
                                   (node_type_blog, node_type_post),
                                   replace_existing=False)

    proj_id = proj['_id']
    r, _, _, status = put_internal('projects', remove_private_keys(proj), _id=proj_id)
    if status != 200:
        log.error('Error %i storing altered project %s %s', status, proj_id, r)
        return 4
    log.info('Project saved succesfully.')

    # Create a blog node.
    nodes_coll = db['nodes']
    blog = nodes_coll.find_one({'node_type': 'blog', 'project': proj_id})
    if not blog:
        blog = {
            u'node_type': node_type_blog['name'],
            u'name': u'Blog',
            u'description': u'',
            u'properties': {},
            u'project': proj_id,
        }
        r, _, _, status = post_internal('nodes', blog)
        if status != 201:
            log.error('Error %i storing blog node: %s', status, r)
            return 4
        log.info('Blog node saved succesfully: %s', r)
    else:
        log.info('Blog node already exists: %s', blog)

    return 0
