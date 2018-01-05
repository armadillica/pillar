from .routes import blueprint_search
from . import queries


def setup_app(app, url_prefix: str = None):
    app.register_api_blueprint(
        blueprint_search, url_prefix=url_prefix)

    queries.setup_app(app)
