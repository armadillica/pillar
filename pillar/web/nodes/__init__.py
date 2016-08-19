from .routes import blueprint


def setup_app(app, url_prefix=None):
    app.register_blueprint(blueprint, url_prefix=url_prefix)
