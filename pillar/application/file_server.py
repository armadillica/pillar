import os
import hashlib
from datetime import datetime
from PIL import Image
from bson import ObjectId
from flask import Blueprint
from flask import request
from application import app
from application import db
from application import post_item
from application.utils.imaging import generate_local_thumbnails


RFC1123_DATE_FORMAT = '%a, %d %b %Y %H:%M:%S GMT'


file_server = Blueprint('file_server', __name__,
                        template_folder='templates',
                        static_folder='static/storage')


def hashfile(afile, hasher, blocksize=65536):
    buf = afile.read(blocksize)
    while len(buf) > 0:
        hasher.update(buf)
        buf = afile.read(blocksize)
    return hasher.hexdigest()


@file_server.route('/build_thumbnails/<path:file_path>')
def build_thumbnails(file_path):
    # Search file with backend "pillar" and path=file_path
    file_ = db.files.find({"path": "{0}".format(file_path)})
    file_ = file_[0]
    user = file_['user']

    file_full_path = os.path.join(app.config['FILE_STORAGE'],file_path)
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
            description="Preview of file {0}".format(file_['name']),
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
            backend='pillar',
            path=path)
        # Commit to database
        r = post_item('files', file_object)
        if r[0]['_status'] == 'ERR':
            return "", r[3] # The error code from the request

    return "", 200


@file_server.route('/file', methods=['POST'])
@file_server.route('/file/<path:file_name>')
def index(file_name=None):
    #GET file
    if file_name:
        return file_server.send_static_file(file_name)
    #POST file
    file_name = request.form['name']
    folder_name = file_name[:2]
    file_folder_path = os.path.join(app.config['FILE_STORAGE'],
                                    folder_name)
    if not os.path.exists(file_folder_path):
        os.mkdir(file_folder_path)
    file_path = os.path.join(file_folder_path, file_name)
    request.files['data'].save(file_path)

    return "{}", 200
