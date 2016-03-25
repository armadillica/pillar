import logging

from bson import ObjectId
from eve.methods.put import put_internal
from flask import Blueprint
from flask import abort
from flask import request
from application import app
from application import utils

encoding = Blueprint('encoding', __name__)
log = logging.getLogger(__name__)


@encoding.route('/zencoder/notifications', methods=['POST'])
def zencoder_notifications():
    if app.config['ENCODING_BACKEND'] != 'zencoder':
        log.warning('Received notification from Zencoder but app not configured for Zencoder.')
        return abort(403)

    if not app.config['DEBUG']:
        # If we are in production, look for the Zencoder header secret
        try:
            notification_secret_request = request.headers[
                'X-Zencoder-Notification-Secret']
        except KeyError:
            log.warning('Received Zencoder notification without secret.')
            return abort(401)
        # If the header is found, check it agains the one in the config
        notification_secret = app.config['ZENCODER_NOTIFICATIONS_SECRET']
        if notification_secret_request != notification_secret:
            log.warning('Received Zencoder notification with incorrect secret.')
            return abort(401)

    # Cast request data into a dict
    data = request.get_json()
    files_collection = app.data.driver.db['files']
    # Find the file object based on processing backend and job_id
    lookup = {'processing.backend': 'zencoder', 'processing.job_id': str(data['job']['id'])}
    f = files_collection.find_one(lookup)
    if not f:
        log.warning('Unknown Zencoder job id %r', data['job']['id'])
        return abort(404)

    file_id = f['_id']
    # Remove internal keys (so that we can run put internal)
    f = utils.remove_private_keys(f)

    # Update processing status
    f['processing']['status'] = data['job']['state']
    # For every variation encoded, try to update the file object
    for output in data['outputs']:
        format = output['format']
        # Change the zencoder 'mpeg4' format to 'mp4' used internally
        format = 'mp4' if format == 'mpeg4' else format
        # Find a variation matching format and resolution
        variation = next((v for v in f['variations'] if v['format'] == format \
                          and v['width'] == output['width']), None)
        # If found, update with delivered file size
        # TODO: calculate md5 on the storage
        if variation:
            variation['length'] = output['file_size_in_bytes']

    put_internal('files', f, _id=ObjectId(file_id))
    return ''
