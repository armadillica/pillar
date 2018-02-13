import concurrent.futures
import logging
import typing

import bson
from flask_script import Manager

from pillar import current_app
from pillar.api.search import index

log = logging.getLogger(__name__)

manager_elastic = Manager(
    current_app, usage="Elastic utilities")

name_to_task = {
    'nodes': index.ResetNodeIndex,
    'users': index.ResetUserIndex,
}
REINDEX_THREAD_COUNT = 5


@manager_elastic.option('indices', nargs='*')
def reset_index(indices: typing.List[str]):
    """
    Destroy and recreate elastic indices

    nodes, users
    """

    with current_app.app_context():
        if not indices:
            indices = name_to_task.keys()

        for elk_index in indices:
            try:
                task = name_to_task[elk_index]()
            except KeyError:
                raise SystemError('Unknown elk_index, choose from %s' %
                                  (', '.join(name_to_task.keys())))
            task.execute()


def _reindex_users():
    db = current_app.db()
    users_coll = db['users']

    # Note that this also finds service accounts, which are filtered out
    # in prepare_user_data(…)
    users = users_coll.find()
    user_count = users.count()
    indexed = 0

    log.info('Reindexing %d users in Elastic', user_count)

    from pillar.celery.search_index_tasks import prepare_user_data
    from pillar.api.search import elastic_indexing

    app = current_app.real_app

    def do_work(work_idx_user):
        nonlocal indexed
        idx, user = work_idx_user

        with app.app_context():
            if idx % 100 == 0:
                log.info('Processing user %d/%d', idx+1, user_count)
            to_index = prepare_user_data('', user=user)
            if not to_index:
                log.debug('not indexing user %s', user)
                return

            try:
                elastic_indexing.push_updated_user(to_index)
            except(KeyError, AttributeError):
                log.exception('Field is missing for %s', user)
            else:
                indexed += 1

    with concurrent.futures.ThreadPoolExecutor(max_workers=REINDEX_THREAD_COUNT) as executor:
        result = executor.map(do_work, enumerate(users))

        # When an exception occurs, it's enough to just iterate over the results.
        # That will re-raise the exception in the main thread.
        for ob in result:
            log.debug('result: %s', ob)
    log.info('Reindexed %d/%d users', indexed, user_count)


def _public_project_ids() -> typing.List[bson.ObjectId]:
    """Returns a list of ObjectIDs of public projects.

    Memoized in setup_app().
    """

    proj_coll = current_app.db('projects')
    result = proj_coll.find({'is_private': False}, {'_id': 1})
    return [p['_id'] for p in result]


def _reindex_nodes():
    db = current_app.db()
    nodes_coll = db['nodes']
    nodes = nodes_coll.find({
        'project': {'$in': _public_project_ids()},
        '_deleted': {'$ne': True},
    })
    node_count = nodes.count()
    indexed = 0

    log.info('Nodes %d will be reindexed in Elastic', node_count)
    app = current_app.real_app

    from pillar.celery.search_index_tasks import prepare_node_data
    from pillar.api.search import elastic_indexing

    def do_work(work_idx_node):
        nonlocal indexed

        idx, node = work_idx_node
        with app.app_context():
            if idx % 100 == 0:
                log.info('Processing node %d/%d', idx+1, node_count)
            try:
                to_index = prepare_node_data('', node=node)
                elastic_indexing.index_node_save(to_index)
            except (KeyError, AttributeError):
                log.exception('Node %s is missing a field', node)
            else:
                indexed += 1

    with concurrent.futures.ThreadPoolExecutor(max_workers=REINDEX_THREAD_COUNT) as executor:
        result = executor.map(do_work, enumerate(nodes))
        # When an exception occurs, it's enough to just iterate over the results.
        # That will re-raise the exception in the main thread.
        for ob in result:
            log.debug('result: %s', ob)
    log.info('Reindexed %d/%d nodes', indexed, node_count)


@manager_elastic.option('indexname', nargs='?')
@manager_elastic.option('-r', '--reset', default=False, action='store_true')
def reindex(indexname='', reset=False):
    import time
    import datetime

    start = time.time()

    if reset:
        log.info('Resetting first')
        reset_index([indexname] if indexname else [])

    if not indexname:
        log.info('reindex everything..')
        _reindex_nodes()
        _reindex_users()
    elif indexname == 'users':
        log.info('Indexing %s', indexname)
        _reindex_users()
    elif indexname == 'nodes':
        log.info('Indexing %s', indexname)
        _reindex_nodes()
    duration = time.time() - start
    log.info('Reindexing took %s', datetime.timedelta(seconds=duration))
