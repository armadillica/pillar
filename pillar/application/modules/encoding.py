from bson import ObjectId
from eve.methods.put import put_internal
from flask import Blueprint
from flask import abort
from flask import request
from application import app

encoding = Blueprint('encoding', __name__)


@encoding.route('/zencoder/notifications', methods=['POST'])
def zencoder_notifications():
    if app.config['ENCODING_BACKEND'] == 'zencoder':
        if not app.config['DEBUG']:
            # If we are in production, look for the Zencoder header secret
            try:
                notification_secret_request = request.headers[
                'X-Zencoder-Notification-Secret']
            except KeyError:
                return abort(401)
            # If the header is found, check it agains the one in the config
            notification_secret = app.config['ZENCODER_NOTIFICATIONS_SECRET']
            if notification_secret_request != notification_secret:
                return abort(401)
        # Cast request data into a dict
        data = request.get_json()
        files_collection = app.data.driver.db['files']
        # Find the file object based on processing backend and job_id
        lookup = {'processing.backend': 'zencoder', 'processing.job_id': str(
            data['job']['id'])}
        f = files_collection.find_one(lookup)
        if f:
            file_id = f['_id']
            # Remove internal keys (so that we can run put internal)
            internal_fields = ['_id', '_etag', '_updated', '_created', '_status']
            for field in internal_fields:
                f.pop(field, None)
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

            r = put_internal('files', f, **{'_id': ObjectId(file_id)})
            return ''
        else:
            return abort(404)
    else:
        return abort(403)
