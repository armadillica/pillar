"""Static file handling"""
import logging

import flask
import flask.views

log = logging.getLogger(__name__)


class PillarStaticFile(flask.views.MethodView):
    def __init__(self, static_folder):
        self.static_folder = static_folder

    def get(self, filename):
        log.debug('Request file %s/%s', self.static_folder, filename)
        return flask.send_from_directory(self.static_folder, filename)
        return flask.send_from_directory(
            self.static_folder, filename,
            conditional=True,
            add_etags=True,
        )
