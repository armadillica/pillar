import os

from flask import Blueprint
from flask import request

from application import app

from PIL import Image

file_server = Blueprint('file_server', __name__,
                        template_folder='templates',
                        static_folder='static/storage')


@file_server.route('/file/thumbnail/<file_name>')
def thumbnail(file_name=None):
    folder_name = file_name[:2]
    file_folder_path = os.path.join(app.config['FILE_STORAGE'],
                                    folder_name)
    # The original file exists?
    file_path = os.path.join(file_folder_path, file_name)
    if not os.path.isfile(file_path):
        return "", 404

    format_ = "jpeg"
    formats = ["jpeg", "png"]
    size = "s"
    sizes = ["xs", "s", "m", "l", "xl"]
    size_dict= {
        "xs": (32, 32),
        "s": (64, 64),
        "m": (128, 128),
        "l": (640, 480),
        "xl": (1024, 768)
        }
    if "format" in request.args:
        if request.args['format'] in formats:
            format_ = request.args['format']
    if "size" in request.args:
        if request.args['size'] in sizes:
            size = request.args['size']
    
    # The Thumbnail already exist?
    thumbnail_folder_path = os.path.join(file_folder_path, size)
    thumbnail_file_path = os.path.join(thumbnail_folder_path, file_name)
    if os.path.isfile(thumbnail_file_path):
        file_static_path = os.path.join("", folder_name, size, file_name)
        return file_server.send_static_file(file_static_path)

    # Create thumbnail
    if not os.path.exists(thumbnail_folder_path):
        os.mkdir(thumbnail_folder_path)
    if not os.path.isfile(thumbnail_file_path):
        try:
            im = Image.open(file_path)
        except IOError:
            return "", 500
        im.thumbnail(size_dict[size]) 
        try:
            im.save(thumbnail_file_path)
        except IOError:
            raise
            return "", 500

        file_static_path = os.path.join("", folder_name, size, file_name)
        return file_server.send_static_file(file_static_path)
    return "", 500

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
