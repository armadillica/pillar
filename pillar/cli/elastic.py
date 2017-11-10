import logging

from flask_script import Manager

from pillar import current_app

log = logging.getLogger(__name__)

manager_elk = Manager(
    current_app, usage="Elastic utilities, like reset_index()")


@manager_elk.command
def reset_index(elk_index):
    """
    Destroy and recreate elastic indices

    node, user ...
    """
    #real_current_app = current_app._get_current_object()._get_current_object()

    with current_app.app_context():
        from pillar.api.search import index
        if elk_index == 'nodes':
            index.reset_node_index()


@manager_elk.command
def reindex_nodes():

    db = current_app.db()
    nodes_coll = db['nodes']
    node_count = nodes_coll.count()

    log.debug('Reindexing %d in Elastic', node_count)

    from pillar.celery.search_index_tasks import prepare_node_data
    from pillar.api.search import elastic_indexing

    for node in nodes_coll.find():
        to_index = prepare_node_data('', node=node)
        elastic_indexing.index_node_save(to_index)
