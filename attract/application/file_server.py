import os
import hashlib

from flask import Blueprint
from flask import request

from application import app
from application import post_item

from datetime import datetime

from PIL import Image

from bson import ObjectId

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


@file_server.route('/build_previews/<file_name>')
def build_previews(file_name=None):
    from pymongo import MongoClient

    # Get File
    client = MongoClient()
    db = client.eve
    file_ = db.files.find({"path": "{0}".format(file_name)})
    file_ = file_[0]
    user = file_['user']

    folder_name = file_name[:2]
    file_folder_path = os.path.join(app.config['FILE_STORAGE'],
                                    folder_name)
    # The original file exists?
    file_path = os.path.join(file_folder_path, file_name)
    if not os.path.isfile(file_path):
        return "", 404

    sizes = ["xs", "s", "m", "l", "xl"]
    size_dict = {
        "xs": (32, 32),
        "s": (64, 64),
        "m": (128, 128),
        "l": (640, 480),
        "xl": (1024, 768)
        }

    # Generate
    preview_list = []
    for size in sizes:
        resized_file_name = "{0}_{1}".format(size, file_name)
        resized_file_path = os.path.join(
            app.config['FILE_STORAGE'],
            resized_file_name)

        # Create thumbnail
        #if not os.path.isfile(resized_file_path):
        try:
            im = Image.open(file_path)
        except IOError:
            return "", 500
        im.thumbnail(size_dict[size])
        width = im.size[0]
        height = im.size[1]
        format = im.format.lower()
        try:
            im.save(resized_file_path)
        except IOError:
            return "", 500

        # file_static_path = os.path.join("", folder_name, size, file_name)
        picture_file_file = open(resized_file_path, 'rb')
        hash_ = hashfile(picture_file_file, hashlib.md5())
        name = "{0}{1}".format(hash_,
                                os.path.splitext(file_name)[1])
        picture_file_file.close()
        description = "Thumbnail {0} for file {1}".format(
            size, file_name)

        prop = {}
        prop['name'] = resized_file_name
        prop['description'] = description
        prop['user'] = user
        # Preview properties:
        prop['is_preview'] = True
        prop['size'] = size
        prop['format'] = format
        prop['width'] = width
        prop['height'] = height
        # TODO set proper contentType and length
        prop['contentType'] = 'image/png'
        prop['length'] = 0
        prop['uploadDate'] = datetime.strftime(
            datetime.now(), RFC1123_DATE_FORMAT)
        prop['md5'] = hash_
        prop['filename'] = resized_file_name
        prop['backend'] = 'attract'
        prop['path'] = name

        entry = post_item ('files', prop)
        if entry[0]['_status'] == 'ERR':
            entry = db.files.find({"path": name})

        entry = entry[0]
        prop['_id'] = entry['_id']

        new_folder_name = name[:2]
        new_folder_path = os.path.join(
            app.config['FILE_STORAGE'],
            new_folder_name)
        new_file_path = os.path.join(
            new_folder_path,
            name)

        if not os.path.exists(new_folder_path):
            os.makedirs(new_folder_path)

        # Clean up temporary file
        os.rename(
            resized_file_path,
            new_file_path)

        preview_list.append(str(prop['_id']))
        #print (new_file_path)

    # Add previews to file
    previews = []
    try:
        previews = file_['previews']
    except KeyError:
        pass

    preview_list = preview_list + previews

    #print (previews)
    #print (preview_list)
    #print (file_['_id'])

    file_ = db.files.update(
        {"_id": ObjectId(file_['_id'])},
        {"$set": {"previews": preview_list}}
    )

    #print (file_)

    return "", 200


@file_server.route('/file', methods=['POST'])
@file_server.route('/file/<file_name>')
def index(file_name=None):
    #GET file
    if file_name:
        folder_name = file_name[:2]
        file_path = os.path.join("", folder_name, file_name)
        return file_server.send_static_file(file_path)
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
