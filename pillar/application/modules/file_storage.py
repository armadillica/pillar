import datetime
import logging
import os
from multiprocessing import Process
from hashlib import md5

import bson.tz_util
import eve.utils
import pymongo
from bson import ObjectId
from eve.methods.patch import patch_internal
from eve.methods.put import put_internal
from flask import Blueprint, safe_join
from flask import jsonify
from flask import request
from flask import abort
from flask import send_from_directory
from flask import url_for, helpers
from flask import current_app

from application import utils
from application.utils import remove_private_keys
from application.utils.cdn import hash_file_path
from application.utils.encoding import Encoder
from application.utils.gcs import GoogleCloudStorageBucket
from application.utils.imaging import ffmpeg_encode
from application.utils.imaging import generate_local_thumbnails
from application.utils.imaging import get_video_data
from application.utils.storage import push_to_storage

log = logging.getLogger(__name__)

file_storage = Blueprint('file_storage', __name__,
                         template_folder='templates',
                         static_folder='../../static/storage', )


@file_storage.route('/gcs/<bucket_name>/<subdir>/')
@file_storage.route('/gcs/<bucket_name>/<subdir>/<path:file_path>')
def browse_gcs(bucket_name, subdir, file_path=None):
    """Browse the content of a Google Cloud Storage bucket"""

    # Initialize storage client
    storage = GoogleCloudStorageBucket(bucket_name, subdir=subdir)
    if file_path:
        # If we provided a file_path, we try to fetch it
        file_object = storage.Get(file_path)
        if file_object:
            # If it exists, return file properties in a dictionary
            return jsonify(file_object)
        else:
            listing = storage.List(file_path)
            return jsonify(listing)
            # We always return an empty listing even if the directory does not
            # exist. This can be changed later.
            # return abort(404)

    else:
        listing = storage.List('')
        return jsonify(listing)


# @file_storage.route('/build_thumbnails/<path:file_path>')
def build_thumbnails(file_path=None, file_id=None):
    """Given a file path or file ObjectId pointing to an image file, fetch it
    and generate a set of predefined variations (using generate_local_thumbnails).
    Return a list of dictionaries containing the various image properties and
    variation properties.
    """

    files_collection = current_app.data.driver.db['files']
    if file_path:
        # Search file with backend "pillar" and path=file_path
        file_ = files_collection.find({"file_path": "{0}".format(file_path)})
        file_ = file_[0]

    if file_id:
        file_ = files_collection.find_one({"_id": ObjectId(file_id)})
        file_path = file_['name']

    file_full_path = safe_join(safe_join(current_app.config['SHARED_DIR'], file_path[:2]),
                               file_path)
    # Does the original file exist?
    if not os.path.isfile(file_full_path):
        return "", 404
    else:
        thumbnails = generate_local_thumbnails(file_full_path,
                                               return_image_stats=True)

    file_variations = []
    for size, thumbnail in thumbnails.iteritems():
        if thumbnail.get('exists'):
            # If a thumbnail was already made, we just continue
            continue
        basename = os.path.basename(thumbnail['file_path'])
        root, ext = os.path.splitext(basename)
        file_variation = dict(
            size=size,
            format=ext[1:],
            width=thumbnail['width'],
            height=thumbnail['height'],
            content_type=thumbnail['content_type'],
            length=thumbnail['length'],
            md5=thumbnail['md5'],
            file_path=basename,
        )
        # XXX Inject is_public for size 't' (should be part of the upload),
        # and currently we set it here and then on the fly during blob
        # creation by simply parsing the extension of the filename. This is
        # bad.
        if size == 't':
            file_variation['is_public'] = True

        file_variations.append(file_variation)

    return file_variations


@file_storage.route('/file', methods=['POST'])
@file_storage.route('/file/<path:file_name>', methods=['GET', 'POST'])
def index(file_name=None):

    # GET file -> read it
    if request.method == 'GET':
        return send_from_directory(current_app.config['STORAGE_DIR'], file_name)

    # POST file -> save it

    # Sanitize the filename; source: http://stackoverflow.com/questions/7406102/
    file_name = request.form['name']
    keepcharacters = {' ', '.', '_'}
    file_name = ''.join(
        c for c in file_name if c.isalnum() or c in keepcharacters).strip()
    file_name = file_name.lstrip('.')

    # Determine & create storage directory
    folder_name = file_name[:2]
    file_folder_path = helpers.safe_join(current_app.config['STORAGE_DIR'], folder_name)
    if not os.path.exists(file_folder_path):
        log.info('Creating folder path %r', file_folder_path)
        os.mkdir(file_folder_path)

    # Save uploaded file
    file_path = helpers.safe_join(file_folder_path, file_name)
    log.info('Saving file %r', file_path)
    request.files['data'].save(file_path)

    # TODO: possibly nicer to just return a redirect to the file's URL.
    return jsonify({'url': url_for('file_storage.index', file_name=file_name)})


def process_file(file_id, src_file):
    """Process the file.

    :param file_id: '_id' key of the file
    :param src_file: POSTed data of the file, lacks private properties.
    """

    src_file = utils.remove_private_keys(src_file)

    filename = src_file['name']
    file_abs_path = safe_join(safe_join(current_app.config['SHARED_DIR'], filename[:2]), filename)

    if not os.path.exists(file_abs_path):
        log.warning("POSTed file document %r refers to non-existant file on file system %s!",
                    file_id, file_abs_path)
        abort(422, "POSTed file document refers to non-existant file on file system!")

    src_file['length'] = os.stat(file_abs_path).st_size
    content_type = src_file['content_type'].split('/')
    src_file['format'] = content_type[1]
    mime_type = content_type[0]
    src_file['file_path'] = filename

    if mime_type == 'image':
        from PIL import Image
        im = Image.open(file_abs_path)
        res = im.size
        src_file['width'] = res[0]
        src_file['height'] = res[1]
        # Generate previews
        src_file['variations'] = build_thumbnails(file_id=file_id)
    elif mime_type == 'video':
        pass
        # Generate variations
        src_video_data = get_video_data(file_abs_path)
        variations = {
            'mp4': None,
            'webm': None
        }
        if src_video_data['duration']:
            src_file['duration'] = src_video_data['duration']

        # Properly resize the video according to 720p and 1080p resolutions
        if src_video_data['res_y'] < 1080:
            res_y = 720
        elif src_video_data['res_y'] >= 1080:
            res_y = 1080

        # Add variations property to the file
        src_file['variations'] = []
        # Create variations
        for v in variations:
            root, ext = os.path.splitext(filename)
            filename = "{0}-{1}p.{2}".format(root, res_y, v)
            video_duration = None
            if src_video_data['duration']:
                video_duration = src_video_data['duration']

            file_variation = dict(
                size="{0}p".format(res_y),
                duration=video_duration,
                format=v,
                width=src_video_data['res_x'],
                height=src_video_data['res_y'],
                content_type="video/{0}".format(v),
                length=0,  # Available after encode
                md5="",  # Available after encode
                file_path=filename,
            )
            # Append file variation
            src_file['variations'].append(file_variation)

        def encode(src_path, src_file, res_y):
            # For every variation in the list call video_encode
            # print "encoding {0}".format(variations)
            if current_app.config['ENCODING_BACKEND'] == 'zencoder':
                # Move the source file in place on the remote storage (which can
                # be accessed from zencoder)
                push_to_storage(str(src_file['project']), src_path)
                j = Encoder.job_create(src_file)
                try:
                    if j:
                        src_file['processing'] = dict(
                            status='pending',
                            job_id="{0}".format(j['process_id']),
                            backend=j['backend'])
                        # Add the processing status to the file object
                        r = put_internal('files',
                                         src_file, **{'_id': ObjectId(file_id)})
                        pass
                except KeyError:
                    pass
            elif current_app.config['ENCODING_BACKEND'] == 'local':
                for v in src_file['variations']:
                    path = ffmpeg_encode(src_path, v['format'], res_y)
                    # Update size data after encoding
                    v['length'] = os.stat(path).st_size

                r = put_internal('files', src_file, **{'_id': ObjectId(file_id)})
                # When all encodes are done, delete source file
                sync_path = os.path.split(src_path)[0]
                push_to_storage(str(src_file['project']), sync_path)

        p = Process(target=encode, args=(file_abs_path, src_file, res_y))
        p.start()
    else:
        log.info("POSTed file was of type %r, which isn't thumbnailed/encoded.", mime_type)

    if mime_type != 'video':
        # Sync the whole subdir
        sync_path = os.path.split(file_abs_path)[0]
        # push_to_storage(str(src_file['project']), sync_path)
        p = Process(target=push_to_storage, args=(
            str(src_file['project']), sync_path))
        p.start()

    # Update the original file with additional info, e.g. image resolution
    put_internal('files', src_file, _id=ObjectId(file_id))


def delete_file(file_item):
    def process_file_delete(file_item):
        """Given a file item, delete the actual file from the storage backend.
        This function can be probably made self-calling."""
        if file_item['backend'] == 'gcs':
            storage = GoogleCloudStorageBucket(str(file_item['project']))
            storage.Delete(file_item['file_path'])
            # Delete any file variation found in the file_item document
            if 'variations' in file_item:
                for v in file_item['variations']:
                    storage.Delete(v['file_path'])
            return True
        elif file_item['backend'] == 'pillar':
            pass
        elif file_item['backend'] == 'cdnsun':
            pass
        else:
            pass

    files_collection = current_app.data.driver.db['files']
    # Collect children (variations) of the original file
    children = files_collection.find({'parent': file_item['_id']})
    for child in children:
        process_file_delete(child)
    # Finally remove the original file
    process_file_delete(file_item)


def generate_link(backend, file_path, project_id=None, is_public=False):
    """Hook to check the backend of a file resource, to build an appropriate link
    that can be used by the client to retrieve the actual file.
    """

    if backend == 'gcs':
        storage = GoogleCloudStorageBucket(project_id)
        blob = storage.Get(file_path)
        if blob and not is_public:
            link = blob['signed_url']
        elif blob and is_public:
            link = blob['public_url']
        else:
            link = None
    elif backend == 'pillar':
        link = url_for('file_storage.index', file_name=file_path, _external=True,
                       _scheme=current_app.config['SCHEME'])
    elif backend == 'cdnsun':
        link = hash_file_path(file_path, None)
    elif backend == 'unittest':
        link = md5(file_path).hexdigest()
    else:
        link = None
    return link


def before_returning_file(response):
    ensure_valid_link(response)


def before_returning_files(response):
    for item in response['_items']:
        ensure_valid_link(item)


def ensure_valid_link(response):
    """Ensures the file item has valid file links using generate_link(...)."""

    # log.debug('Inspecting link for file %s', response['_id'])

    # Check link expiry.
    now = datetime.datetime.now(tz=bson.tz_util.utc)
    if 'link_expires' in response:
        link_expires = response['link_expires']
        if now < link_expires:
            # Not expired yet, so don't bother regenerating anything.
            log.debug('Link expires at %s, which is in the future, so not generating new link',
                      link_expires)
            return

        log.debug('Link expired at %s, which is in the past; generating new link', link_expires)
    else:
        log.debug('No expiry date for link; generating new link')

    _generate_all_links(response, now)


def _generate_all_links(response, now):
    """Generate a new link for the file and all its variations.

    :param response: the file document that should be updated.
    :param now: datetime that reflects 'now', for consistent expiry generation.
    """

    project_id = str(
        response['project']) if 'project' in response else None  # TODO: add project id to all files
    backend = response['backend']
    response['link'] = generate_link(backend, response['file_path'], project_id)
    if 'variations' in response:
        for variation in response['variations']:
            variation['link'] = generate_link(backend, variation['file_path'], project_id)

    # Construct the new expiry datetime.
    validity_secs = current_app.config['FILE_LINK_VALIDITY'][backend]
    response['link_expires'] = now + datetime.timedelta(seconds=validity_secs)

    patch_info = remove_private_keys(response)
    (patch_resp, _, _, _) = patch_internal('files', patch_info, _id=ObjectId(response['_id']))
    if patch_resp.get('_status') == 'ERR':
        log.warning('Unable to save new links for file %s: %r', response['_id'], patch_resp)
        # TODO: raise a snag.
        response['_updated'] = now
    else:
        response['_updated'] = patch_resp['_updated']


def post_POST_files(request, payload):
    """After an file object has been created, we do the necessary processing
    and further update it.
    """

    if 200 <= payload.status_code < 300:
        import json
        posted_properties = json.loads(request.data)
        private_properties = json.loads(payload.data)
        file_id = private_properties['_id']

        process_file(file_id, posted_properties)


def before_deleting_file(item):
    delete_file(item)


def on_pre_get_files(_, lookup):
    # Override the HTTP header, we always want to fetch the document from MongoDB.
    parsed_req = eve.utils.parse_request('files')
    parsed_req.if_modified_since = None

    # Only fetch it if the date got expired.
    now = datetime.datetime.now(tz=bson.tz_util.utc)
    lookup_expired = lookup.copy()
    lookup_expired['link_expires'] = {'$lte': now}

    cursor = current_app.data.find('files', parsed_req, lookup_expired)
    for file_doc in cursor:
        log.debug('Updating expired links for file %r.', file_doc['_id'])
        _generate_all_links(file_doc, now)


def refresh_links_for_project(project_uuid, chunk_size, expiry_seconds):
    if chunk_size:
        log.info('Refreshing the first %i links for project %s', chunk_size, project_uuid)
    else:
        log.info('Refreshing all links for project %s', project_uuid)

    # Retrieve expired links.
    files_collection = current_app.data.driver.db['files']

    now = datetime.datetime.now(tz=bson.tz_util.utc)
    expire_before = now + datetime.timedelta(seconds=expiry_seconds)
    log.info('Limiting to links that expire before %s', expire_before)

    to_refresh = files_collection.find(
        {'project': ObjectId(project_uuid),
         'link_expires': {'$lt': expire_before},
         }).sort([('link_expires', pymongo.ASCENDING)]).limit(chunk_size)

    if to_refresh.count() == 0:
        log.info('No links to refresh.')
        return

    for file_doc in to_refresh:
        log.debug('Refreshing links for file %s', file_doc['_id'])
        _generate_all_links(file_doc, now)

    log.info('Refreshed %i links', min(chunk_size, to_refresh.count()))


def refresh_links_for_backend(backend_name, chunk_size, expiry_seconds):
    from flask import current_app

    # Retrieve expired links.
    files_collection = current_app.data.driver.db['files']

    now = datetime.datetime.now(tz=bson.tz_util.utc)
    expire_before = now + datetime.timedelta(seconds=expiry_seconds)
    log.info('Limiting to links that expire before %s', expire_before)

    to_refresh = files_collection.find(
        {'$or': [{'backend': backend_name, 'link_expires': None},
                 {'backend': backend_name, 'link_expires': {'$lt': expire_before}},
                 {'backend': backend_name, 'link': None}]
        }).sort([('link_expires', pymongo.ASCENDING)]).limit(chunk_size)

    if to_refresh.count() == 0:
        log.info('No links to refresh.')
        return

    for file_doc in to_refresh:
        log.debug('Refreshing links for file %s', file_doc['_id'])
        _generate_all_links(file_doc, now)

    log.info('Refreshed %i links', min(chunk_size, to_refresh.count()))


def setup_app(app, url_prefix):
    app.on_pre_GET_files += on_pre_get_files
    app.on_post_POST_files += post_POST_files

    app.on_fetched_item_files += before_returning_file
    app.on_fetched_resource_files += before_returning_files

    app.on_delete_item_files += before_deleting_file

    app.register_blueprint(file_storage, url_prefix=url_prefix)
