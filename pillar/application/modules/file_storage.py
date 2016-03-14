import logging
import os
from multiprocessing import Process
from bson import ObjectId
from flask import request
from flask import Blueprint
from flask import jsonify
from flask import send_from_directory
from flask import url_for, helpers
from eve.methods.put import put_internal
from application import app
from application.utils.imaging import generate_local_thumbnails
from application.utils.imaging import get_video_data
from application.utils.imaging import ffmpeg_encode
from application.utils.storage import push_to_storage
from application.utils.cdn import hash_file_path
from application.utils.gcs import GoogleCloudStorageBucket
from application.utils.encoding import Encoder


log = logging.getLogger(__name__)

file_storage = Blueprint('file_storage', __name__,
                         template_folder='templates',
                         static_folder='../../static/storage',)


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


#@file_storage.route('/build_thumbnails/<path:file_path>')
def build_thumbnails(file_path=None, file_id=None):
    """Given a file path or file ObjectId pointing to an image file, fetch it
    and generate a set of predefined variations (using generate_local_thumbnails).
    Return a list of dictionaries containing the various image properties and
    variation properties.
    """
    files_collection = app.data.driver.db['files']
    if file_path:
        # Search file with backend "pillar" and path=file_path
        file_ = files_collection.find({"file_path": "{0}".format(file_path)})
        file_ = file_[0]

    if file_id:
        file_ = files_collection.find_one({"_id": ObjectId(file_id)})
        file_path = file_['name']

    file_full_path = os.path.join(app.config['SHARED_DIR'], file_path[:2],
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
        return send_from_directory(app.config['STORAGE_DIR'], file_name)

    # POST file -> save it

    # Sanitize the filename; source: http://stackoverflow.com/questions/7406102/
    file_name = request.form['name']
    keepcharacters = {' ', '.', '_'}
    file_name = ''.join(
        c for c in file_name if c.isalnum() or c in keepcharacters).strip()
    file_name = file_name.lstrip('.')

    # Determine & create storage directory
    folder_name = file_name[:2]
    file_folder_path = helpers.safe_join(app.config['STORAGE_DIR'], folder_name)
    if not os.path.exists(file_folder_path):
        log.info('Creating folder path %r', file_folder_path)
        os.mkdir(file_folder_path)

    # Save uploaded file
    file_path = helpers.safe_join(file_folder_path, file_name)
    log.info('Saving file %r', file_path)
    request.files['data'].save(file_path)

    # TODO: possibly nicer to just return a redirect to the file's URL.
    return jsonify({'url': url_for('file_storage.index', file_name=file_name)})


def process_file(src_file):
    """Process the file
    """
    file_id = src_file['_id']
    # Remove properties that do not belong in the collection
    internal_fields = ['_id', '_etag', '_updated', '_created', '_status']
    for field in internal_fields:
        src_file.pop(field, None)

    files_collection = app.data.driver.db['files']
    file_abs_path = os.path.join(
        app.config['SHARED_DIR'], src_file['name'][:2], src_file['name'])

    src_file['length'] = os.stat(file_abs_path).st_size
    content_type = src_file['content_type'].split('/')
    src_file['format'] = content_type[1]
    mime_type = content_type[0]
    src_file['file_path'] = src_file['name']

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
            root, ext = os.path.splitext(src_file['name'])
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
                length=0, # Available after encode
                md5="", # Available after encode
                file_path=filename,
                )
            # Append file variation
            src_file['variations'].append(file_variation)

        def encode(src_path, src_file, res_y):
            # For every variation in the list call video_encode
            # print "encoding {0}".format(variations)
            if app.config['ENCODING_BACKEND'] == 'zencoder':
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
            elif app.config['ENCODING_BACKEND'] == 'local':
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
    if mime_type != 'video':
        # Sync the whole subdir
        sync_path = os.path.split(file_abs_path)[0]
        # push_to_storage(str(src_file['project']), sync_path)
        p = Process(target=push_to_storage, args=(
            str(src_file['project']), sync_path))
        p.start()

    # Update the original file with additional info, e.g. image resolution
    r = put_internal('files', src_file, **{'_id': ObjectId(file_id)})


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
    files_collection = app.data.driver.db['files']
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
        _scheme=app.config['SCHEME'])
    elif backend == 'cdnsun':
        link = hash_file_path(file_path, None)
    else:
        link = None
    return link
