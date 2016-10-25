def append_custom_node_endpoints():
    pass


def setup_app(app):
    from . import posts

    posts.setup_app(app)
