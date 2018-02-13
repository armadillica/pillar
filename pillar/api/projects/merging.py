"""Code for merging projects."""
import logging

from bson import ObjectId

from pillar import current_app
from pillar.api.file_storage.moving import move_to_bucket
from pillar.api.utils import random_etag, utcnow

log = logging.getLogger(__name__)


def merge_project(pid_from: ObjectId, pid_to: ObjectId):
    """Move nodes and files from one project to another.

    Note that this may invalidate the nodes, as their node type definition
    may differ between projects.
    """
    log.info('Moving project contents from %s to %s', pid_from, pid_to)
    assert isinstance(pid_from, ObjectId)
    assert isinstance(pid_to, ObjectId)

    files_coll = current_app.db('files')
    nodes_coll = current_app.db('nodes')

    # Move the files first. Since this requires API calls to an external
    # service, this is more likely to go wrong than moving the nodes.
    to_move = files_coll.find({'project': pid_from}, projection={'_id': 1})
    log.info('Moving %d files to project %s', to_move.count(), pid_to)
    for file_doc in to_move:
        fid = file_doc['_id']
        log.debug('moving file %s to project %s', fid, pid_to)
        move_to_bucket(fid, pid_to)

    # Mass-move the nodes.
    etag = random_etag()
    result = nodes_coll.update_many(
        {'project': pid_from},
        {'$set': {'project': pid_to,
                  '_etag': etag,
                  '_updated': utcnow(),
                  }}
    )
    log.info('Moved %d nodes to project %s', result.modified_count, pid_to)
