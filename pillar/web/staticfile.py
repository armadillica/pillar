"""Static file handling"""

import flask
import flask.views


class PillarStaticFile(flask.views.MethodView):
    def __init__(self, static_folder):
        self.static_folder = static_folder

    def get(self, filename):
        return flask.send_from_directory(self.static_folder, filename)
