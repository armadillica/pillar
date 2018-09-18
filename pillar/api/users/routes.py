import logging

from eve.methods.get import get
from flask import Blueprint, request
import werkzeug.exceptions as wz_exceptions

from pillar import current_app
from pillar.api import utils
from pillar.api.utils.authorization import require_login
from pillar.auth import current_user

log = logging.getLogger(__name__)
blueprint_api = Blueprint('users_api', __name__)


@blueprint_api.route('/me')
@require_login()
def my_info():
    eve_resp, _, _, status, _ = get('users', {'_id': current_user.user_id})
    resp = utils.jsonify(eve_resp['_items'][0], status=status)
    return resp


@blueprint_api.route('/video/<video_id>/progress')
@require_login()
def get_video_progress(video_id: str):
    """Return video progress information.

    Either a `204 No Content` is returned (no information stored),
    or a `200 Ok` with JSON from Eve's 'users' schema, from the key
    video.view_progress.<video_id>.
    """

    # Validation of the video ID; raises a BadRequest when it's not an ObjectID.
    # This isn't strictly necessary, but it makes this function behave symmetrical
    # to the set_video_progress() function.
    utils.str2id(video_id)

    users_coll = current_app.db('users')
    user_doc = users_coll.find_one(current_user.user_id, projection={'nodes.view_progress': True})
    try:
        progress = user_doc['nodes']['view_progress'][video_id]
    except KeyError:
        return '', 204
    if not progress:
        return '', 204

    return utils.jsonify(progress)


@blueprint_api.route('/video/<video_id>/progress', methods=['POST'])
@require_login()
def set_video_progress(video_id: str):
    """Save progress information about a certain video.

    Expected parameters:
    - progress_in_sec: float number of seconds
    - progress_in_perc: integer percentage of video watched (interval [0-100])
    """
    my_log = log.getChild('set_video_progress')
    my_log.debug('Setting video progress for user %r video %r', current_user.user_id, video_id)

    # Constructing this response requires an active app, and thus can't be done on module load.
    no_video_response = utils.jsonify({'_message': 'No such video'}, status=404)

    try:
        progress_in_sec = float(request.form['progress_in_sec'])
        progress_in_perc = int(request.form['progress_in_perc'])
    except KeyError as ex:
        my_log.debug('Missing POST field in request: %s', ex)
        raise wz_exceptions.BadRequest(f'missing a form field')
    except ValueError as ex:
        my_log.debug('Invalid value for POST field in request: %s', ex)
        raise wz_exceptions.BadRequest(f'Invalid value for field: {ex}')

    users_coll = current_app.db('users')
    nodes_coll = current_app.db('nodes')

    # First check whether this is actually an existing video
    video_oid = utils.str2id(video_id)
    video_doc = nodes_coll.find_one(video_oid, projection={
        'node_type': True,
        'properties.content_type': True,
        'properties.file': True,
    })
    if not video_doc:
        my_log.debug('Node %r not found, unable to set progress for user %r',
                     video_oid, current_user.user_id)
        return no_video_response

    try:
        is_video = (video_doc['node_type'] == 'asset'
                    and video_doc['properties']['content_type'] == 'video')
    except KeyError:
        is_video = False

    if not is_video:
        my_log.info('Node %r is not a video, unable to set progress for user %r',
                    video_oid, current_user.user_id)
        # There is no video found at this URL, so act as if it doesn't even exist.
        return no_video_response

    # Compute the progress
    percent = min(100, max(0, progress_in_perc))
    progress = {
        'progress_in_sec': progress_in_sec,
        'progress_in_percent': percent,
        'last_watched': utils.utcnow(),
    }

    # After watching a certain percentage of the video, we consider it 'done'
    #
    #                   Total     Credit start  Total  Credit  Percent
    #                   HH:MM:SS  HH:MM:SS      sec    sec     of duration
    # Sintel            00:14:48  00:12:24      888    744     83.78%
    # Tears of Steel    00:12:14  00:09:49      734    589     80.25%
    # Cosmos Laundro    00:12:10  00:10:05      730    605     82.88%
    # Agent 327         00:03:51  00:03:26      231    206     89.18%
    # Caminandes 3      00:02:30  00:02:18      150    138     92.00%
    # Glass Half        00:03:13  00:02:52      193    172     89.12%
    # Big Buck Bunny    00:09:56  00:08:11      596    491     82.38%
    # Elephant’s Drea   00:10:54  00:09:25      654    565     86.39%
    #
    #                                      Median              85.09%
    #                                      Average             85.75%
    #
    # For training videos marking at done at 85% of the video may be a bit
    # early, since those probably won't have (long) credits. This is why we
    # stick to 90% here.
    if percent >= 90:
        progress['done'] = True

    # Setting each property individually prevents us from overwriting any
    # existing {done: true} fields.
    updates = {f'nodes.view_progress.{video_id}.{k}': v
               for k, v in progress.items()}
    result = users_coll.update_one({'_id': current_user.user_id},
                                   {'$set': updates})

    if result.matched_count == 0:
        my_log.error('Current user %r could not be updated', current_user.user_id)
        raise wz_exceptions.InternalServerError('Unable to find logged-in user')

    return '', 204
