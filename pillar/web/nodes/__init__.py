from .routes import blueprint


def setup_app(app, url_prefix=None):
    from . import custom

    custom.setup_app(app)
    app.register_blueprint(blueprint, url_prefix=url_prefix)
