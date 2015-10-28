import os
import json
from multiprocessing import Process
from bson import ObjectId
from flask import request
from flask import Blueprint
from flask import abort
from flask import jsonify
from flask import send_from_directory
from application import app
from application import post_item
from application.utils.imaging import generate_local_thumbnails
from application.utils.imaging import get_video_data
from application.utils.imaging import ffmpeg_encode
from application.utils.storage import remote_storage_sync
from application.utils.gcs import GoogleCloudStorageBucket

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


@file_storage.route('/build_thumbnails/<path:file_path>')
def build_thumbnails(file_path=None, file_id=None):
    files_collection = app.data.driver.db['files']
    if file_path:
        # Search file with backend "pillar" and path=file_path
        file_ = files_collection.find({"path": "{0}".format(file_path)})
        file_ = file_[0]

    if file_id:
        file_ = files_collection.find_one({"_id": ObjectId(file_id)})
        file_path = file_['name']

    user = file_['user']

    file_full_path = os.path.join(app.config['STORAGE_DIR'], file_path)
    # Does the original file exist?
    if not os.path.isfile(file_full_path):
        return "", 404
    else:
        thumbnails = generate_local_thumbnails(file_full_path,
            return_image_stats=True)

    for size, thumbnail in thumbnails.iteritems():
        if thumbnail.get('exists'):
            # If a thumbnail was already made, we just continue
            continue
        basename = os.path.basename(thumbnail['path'])
        root, ext = os.path.splitext(basename)
        path = os.path.join(basename[:2], basename)
        file_object = dict(
            name=root,
            #description="Preview of file {0}".format(file_['name']),
            user=user,
            parent=file_['_id'],
            size=size,
            format=ext[1:],
            width=thumbnail['width'],
            height=thumbnail['height'],
            content_type=thumbnail['content_type'],
            length=thumbnail['length'],
            md5=thumbnail['md5'],
            filename=basename,
            backend=file_['backend'],
            path=path)
        # Commit to database
        r = post_item('files', file_object)
        if r[0]['_status'] == 'ERR':
            return "", r[3] # The error code from the request

    return "", 200


@file_storage.route('/file', methods=['POST'])
@file_storage.route('/file/<path:file_name>')
def index(file_name=None):
    #GET file
    if file_name:
        return send_from_directory(app.config['STORAGE_DIR'], file_name)
    #POST file
    file_name = request.form['name']
    folder_name = file_name[:2]
    file_folder_path = os.path.join(app.config['STORAGE_DIR'],
                                    folder_name)
    if not os.path.exists(file_folder_path):
        os.mkdir(file_folder_path)
    file_path = os.path.join(file_folder_path, file_name)
    request.files['data'].save(file_path)

    return "{}", 200


def process_file(src_file):
    """Process the file
    """

    files_collection = app.data.driver.db['files']

    file_abs_path = os.path.join(app.config['SHARED_DIR'], src_file['name'])
    src_file['length'] = os.stat(file_abs_path).st_size
    # Remove properties that do not belong in the collection
    del src_file['_status']
    del src_file['_links']
    content_type = src_file['content_type'].split('/')
    src_file['format'] = content_type[1]
    mime_type = content_type[0]
    src_file['path'] = src_file['name']

    if mime_type == 'image':
        from PIL import Image
        im = Image.open(file_abs_path)
        res = im.size
        src_file['width'] = res[0]
        src_file['height'] = res[1]
        # Generate previews

        build_thumbnails(file_id=src_file['_id'])
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

        # Create variations in database
        for v in variations:
            root, ext = os.path.splitext(src_file['name'])
            filename = "{0}-{1}p.{2}".format(root, res_y, v)
            video_duration = None
            if src_video_data['duration']:
                video_duration = src_video_data['duration']

            file_object = dict(
                name=os.path.split(filename)[1],
                #description="Preview of file {0}".format(file_['name']),
                user=src_file['user'],
                parent=src_file['_id'],
                size="{0}p".format(res_y),
                duration=video_duration,
                format=v,
                width=src_video_data['res_x'],
                height=src_video_data['res_y'],
                content_type="video/{0}".format(v),
                length=0, # Available after encode
                md5="", # Available after encode
                filename=os.path.split(filename)[1],
                backend=src_file['backend'],
                path=filename)

            file_object_id = files_collection.save(file_object)
            # Append the ObjectId to the new list
            variations[v] = file_object_id


        def encode(src, variations, res_y):
            # For every variation in the list call video_encode
            # print "encoding {0}".format(variations)
            for v in variations:
                path = ffmpeg_encode(file_abs_path, v, res_y)
                # Update size data after encoding
                # (TODO) update status (non existing now)
                file_size = os.stat(path).st_size
                variation = files_collection.find_one(variations[v])
                variation['length'] = file_size
                # print variation
                file_asset = files_collection.find_and_modify(
                    {'_id': variations[v]},
                    variation)

                # rsync the file file (this is async)
                remote_storage_sync(path)
                # When all encodes are done, delete source file


        p = Process(target=encode, args=(file_abs_path, variations, res_y))
        p.start()
    if mime_type != 'video':
         # Sync the whole subdir
        sync_path = os.path.split(file_abs_path)[0]
    else:
        sync_path = file_abs_path
    remote_storage_sync(sync_path)

    files_collection = app.data.driver.db['files']
    file_asset = files_collection.find_and_modify(
        {'_id': src_file['_id']},
        src_file)
