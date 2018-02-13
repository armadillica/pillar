import datetime
import json
import logging
import os

from bson import ObjectId
from flask import Blueprint
from flask import abort
from flask import current_app
from flask import request

from pillar.api import utils
from pillar.api.file_storage_backends import Bucket

encoding = Blueprint('encoding', __name__)
log = logging.getLogger(__name__)


def size_descriptor(width, height):
    """Returns the size descriptor (like '1080p') for the given width.

    >>> size_descriptor(720, 480)
    '576p'
    >>> size_descriptor(1920, 1080)
    '1080p'
    >>> size_descriptor(1920, 751)  # 23:9
    '1080p'
    """

    widths = {
        720: '576p',
        640: '480p',
        1280: '720p',
        1920: '1080p',
        2048: '2k',
        3840: 'UHD',
        4096: '4k',
    }

    # If it is a known width, use it. Otherwise just return '{height}p'
    if width in widths:
        return widths[width]

    return '%ip' % height


@encoding.route('/zencoder/notifications', methods=['POST'])
def zencoder_notifications():
    """

    See: https://app.zencoder.com/docs/guides/getting-started/notifications#api_version_2

    """
    if current_app.config['ENCODING_BACKEND'] != 'zencoder':
        log.warning('Received notification from Zencoder but app not configured for Zencoder.')
        return abort(403)

    if not current_app.config['DEBUG']:
        # If we are in production, look for the Zencoder header secret
        try:
            notification_secret_request = request.headers[
                'X-Zencoder-Notification-Secret']
        except KeyError:
            log.warning('Received Zencoder notification without secret.')
            return abort(401)
        # If the header is found, check it agains the one in the config
        notification_secret = current_app.config['ZENCODER_NOTIFICATIONS_SECRET']
        if notification_secret_request != notification_secret:
            log.warning('Received Zencoder notification with incorrect secret.')
            return abort(401)

    # Cast request data into a dict
    data = request.get_json()

    if log.isEnabledFor(logging.DEBUG):
        from pprint import pformat
        log.debug('Zencoder job JSON: %s', pformat(data))

    files_collection = current_app.data.driver.db['files']
    # Find the file object based on processing backend and job_id
    zencoder_job_id = data['job']['id']
    lookup = {'processing.backend': 'zencoder',
              'processing.job_id': str(zencoder_job_id)}
    file_doc = files_collection.find_one(lookup)
    if not file_doc:
        log.warning('Unknown Zencoder job id %r', zencoder_job_id)
        # Return 200 OK when debugging, or Zencoder will keep trying and trying and trying...
        # which is what we want in production.
        return "Not found, but that's okay.", 200 if current_app.config['DEBUG'] else 404

    file_id = ObjectId(file_doc['_id'])
    # Remove internal keys (so that we can run put internal)
    file_doc = utils.remove_private_keys(file_doc)

    # Update processing status
    job_state = data['job']['state']
    file_doc['processing']['status'] = job_state

    if job_state == 'failed':
        log.warning('Zencoder job %s for file %s failed: %s', zencoder_job_id, file_id,
                    json.dumps(data, sort_keys=True, indent=4))

        file_doc['status'] = 'failed'
        current_app.put_internal('files', file_doc, _id=file_id)

        # This is 'okay' because we handled the Zencoder notification properly.
        return "You failed, but that's okay.", 200

    log.info('Zencoder job %s for file %s completed with status %s.', zencoder_job_id, file_id,
             job_state)

    # For every variation encoded, try to update the file object
    storage_name, _ = os.path.splitext(file_doc['file_path'])
    nice_name, _ = os.path.splitext(file_doc['filename'])

    bucket_class = Bucket.for_backend(file_doc['backend'])
    bucket = bucket_class(str(file_doc['project']))

    for output in data['outputs']:
        video_format = output['format']
        # Change the zencoder 'mpeg4' format to 'mp4' used internally
        video_format = 'mp4' if video_format == 'mpeg4' else video_format

        # Find a variation matching format and resolution
        variation = next((v for v in file_doc['variations']
                          if v['format'] == format and v['width'] == output['width']), None)
        # Fall back to a variation matching just the format
        if variation is None:
            variation = next((v for v in file_doc['variations']
                              if v['format'] == video_format), None)
        if variation is None:
            log.warning('Unable to find variation for video format %s for file %s',
                        video_format, file_id)
            continue

        # Rename the file to include the now-known size descriptor.
        size = size_descriptor(output['width'], output['height'])
        new_fname = f'{storage_name}-{size}.{video_format}'

        # Rename the file on the storage.
        blob = bucket.blob(variation['file_path'])
        try:
            new_blob = bucket.rename_blob(blob, new_fname)
            new_blob.update_filename(f'{nice_name}-{size}.{video_format}')
        except Exception:
            log.warning('Unable to rename blob %r to %r. Keeping old name.',
                        blob, new_fname, exc_info=True)
        else:
            variation['file_path'] = new_fname

        # TODO: calculate md5 on the storage
        variation.update({
            'height': output['height'],
            'width': output['width'],
            'length': output['file_size_in_bytes'],
            'duration': data['input']['duration_in_ms'] / 1000,
            'md5': output['md5_checksum'] or '',  # they don't do MD5 for GCS...
            'size': size,
        })

    file_doc['status'] = 'complete'

    # Force an update of the links on the next load of the file.
    file_doc['link_expires'] = utils.utcnow() - datetime.timedelta(days=1)

    r, _, _, status = current_app.put_internal('files', file_doc, _id=file_id)
    if status != 200:
        log.error('unable to save file %s after Zencoder notification: %s', file_id, r)
        return json.dumps(r), 500

    return '', 204


def setup_app(app, url_prefix):
    app.register_api_blueprint(encoding, url_prefix=url_prefix)
