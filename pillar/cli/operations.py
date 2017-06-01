import logging

from flask_script import Manager
from pillar import current_app

log = logging.getLogger(__name__)

manager_operations = Manager(
    current_app, usage="Backend operations, like moving nodes across projects")


@manager_operations.command
def file_change_backend(file_id, dest_backend='gcs'):
    """Given a file document, move it to the specified backend (if not already
    there) and update the document to reflect that.
    Files on the original backend are not deleted automatically.
    """

    from pillar.api.file_storage.moving import change_file_storage_backend
    change_file_storage_backend(file_id, dest_backend)


@manager_operations.command
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


@manager_operations.command
@manager_operations.option('-p', '--project', dest='dest_proj_url',
                           help='Destination project URL')
@manager_operations.option('-f', '--force', dest='force', action='store_true', default=False,
                           help='Move even when already at the given project.')
@manager_operations.option('-s', '--skip-gcs', dest='skip_gcs', action='store_true', default=False,
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


@manager_operations.command
def index_users_rebuild():
    """Clear users index, update settings and reindex all users."""

    from pillar.api.utils.algolia import algolia_index_user_save

    users_index = current_app.algolia_index_users
    if users_index is None:
        log.error('Algolia is not configured properly, unable to do anything!')
        return 1

    log.info('Dropping existing index: %s', users_index)
    users_index.clear_index()
    index_users_update_settings()

    db = current_app.db()
    users = db['users'].find({'_deleted': {'$ne': True}})

    log.info('Reindexing all users')
    for user in users:
        algolia_index_user_save(user)


@manager_operations.command
def index_users_update_settings():
    """Configure indexing backend as required by the project"""
    users_index = current_app.algolia_index_users

    # Automatically creates index if it does not exist
    users_index.set_settings({
        'searchableAttributes': [
            'full_name',
            'username',
            'email',
            'unordered(roles)'
        ]
    })


@manager_operations.option('args', nargs='*')
def worker(args):
    """Runs a Celery worker."""

    import sys

    argv0 = f'{sys.argv[0]} operations worker'
    argvother = [
        '-E',
        '-l', 'INFO',
        '--concurrency', '1',
        '--pool', 'solo',  # No preforking, as PyMongo can't handle connect-before-fork.
                           # We might get rid of this and go for the default Celery worker
                           # preforking concurrency model, *if* we can somehow reset the
                           # PyMongo client and reconnect after forking.
    ] + list(args)

    from pillar.celery.celery_cfg import celery_cfg

    celery_cfg.worker_main([argv0] + argvother)
