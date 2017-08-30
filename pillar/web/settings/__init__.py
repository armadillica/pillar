from .routes import blueprint


def setup_app(app, url_prefix):
    app.register_blueprint(blueprint, url_prefix=url_prefix)
