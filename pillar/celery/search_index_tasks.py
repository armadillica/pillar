import logging

from . import algolia_tasks

from pillar import current_app

log = logging.getLogger(__name__)


# TODO make index backend conditional on settings.
# now uses angolia, but should use elastic


@current_app.celery.task(ignore_result=True)
def updated_user(user_id: str):
    """Push an update to the index when a user item is updated"""

    algolia_tasks.push_updated_user_to_algolia(user_id)


@current_app.celery.task(ignore_result=True)
def node_save(node_id: str):

    algolia_tasks.index_node_save(node_id)


@current_app.celery.task(ignore_result=True)
def node_delete(node_id: str):

    algolia_tasks.index_node_delete(node_id)
