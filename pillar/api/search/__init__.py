import logging

#import bson
#from flask import current_app

from .routes import blueprint_search

log = logging.getLogger(__name__)


def setup_app(app, url_prefix: str =None):
    app.register_api_blueprint(
        blueprint_search, url_prefix=url_prefix)
