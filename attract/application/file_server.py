import os

from flask import Blueprint
from flask import request

import config

file_server = Blueprint('file_server', __name__,
                        template_folder='templates',
                        static_folder='static/storage')


@file_server.route('/file', methods=['POST'])
@file_server.route('/file/<file_name>')
def index(file_name=None):
    #GET file
    if file_name:
        folder_name = file_name[:2]
        file_path = os.path.join("", folder_name, file_name)
        print (file_path)
        return file_server.send_static_file(file_path)
    #POST file
    file_name = request.form['name']
    folder_name = file_name[:2]
    file_folder_path = os.path.join(config.Development.FILE_STORAGE,
                                    folder_name)
    if not os.path.exists(file_folder_path):
                    os.mkdir(file_folder_path)
    file_path = os.path.join(file_folder_path, file_name)
    request.files['data'].save(file_path)

    return "{}", 200
