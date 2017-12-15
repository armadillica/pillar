import logging

from .routes import blueprint_search

def setup_app(app, url_prefix: str =None):
    app.register_api_blueprint(
        blueprint_search, url_prefix=url_prefix)
