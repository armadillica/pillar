import logging

from flask_script import Manager

from pillar import current_app

log = logging.getLogger(__name__)

manager_elk = Manager(
    current_app, usage="Elastic utilities, like reset_index()")

indexes = ['users', 'nodes']


@manager_elk.command
def reset_index(elk_index=None):
    """
    Destroy and recreate elastic indices

    node, user ...
    """

    with current_app.app_context():
        from pillar.api.search import index
        if not elk_index:
            index.reset_index(indexes)
            return
        if elk_index == 'nodes':
            index.reset_index(['node'])
            return
        if elk_index == 'users':
            index.reset_index(['user'])
            return


def _reindex_users():
    db = current_app.db()
    users_coll = db['users']
    user_count = users_coll.count()

    log.debug('Reindexing %d in Elastic', user_count)

    from pillar.celery.search_index_tasks import prepare_user_data
    from pillar.api.search import elastic_indexing

    for user in users_coll.find():
        to_index = prepare_user_data('', user=user)
        if not to_index:
            log.debug('missing user..')
            continue

        try:
            elastic_indexing.push_updated_user(to_index)
        except(KeyError, AttributeError):
            log.exception('Field is missing for %s', user)
            continue


# stolen from api.latest.
def _public_project_ids() -> typing.List[bson.ObjectId]:
    """Returns a list of ObjectIDs of public projects.

    Memoized in setup_app().
    """

    proj_coll = current_app.db('projects')
    result = proj_coll.find({'is_private': False}, {'_id': 1})
    return [p['_id'] for p in result]


def _reindex_nodes():

    db = current_app.db()
    pipeline = [
        {'$match': {'project': {'$in': _public_project_ids()}}},
    ]
    private_filter = {'project': {'$in': _public_project_ids()}}
    nodes_coll = db['nodes']
    nodes_coll = nodes_coll.find(private_filter)
    node_count = nodes_coll.count()

    log.debug('Reindexing %d in Elastic', node_count)

    from pillar.celery.search_index_tasks import prepare_node_data
    from pillar.api.search import elastic_indexing

    for node in nodes_coll:
        try:
            to_index = prepare_node_data('', node=node)
            elastic_indexing.index_node_save(to_index)
        except(KeyError, AttributeError):
            log.exception('Field is missing for %s', node)
            continue


@manager_elk.command
def reindex(indexname):

    if not indexname:
        log.debug('reindex everything..')
        _reindex_nodes()
        _reindex_users()
    elif indexname == 'users':
        log.debug('Indexing %s', indexname)
        _reindex_users()
    elif indexname == 'nodes':
        log.debug('Indexing %s', indexname)
        _reindex_nodes()
