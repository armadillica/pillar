def setup_app(app):
    from . import main, users, projects, nodes, notifications, redirects
    main.setup_app(app, url_prefix=None)
    users.setup_app(app, url_prefix=None)
    redirects.setup_app(app, url_prefix='/r')
    projects.setup_app(app, url_prefix='/p')
    nodes.setup_app(app, url_prefix='/nodes')
    notifications.setup_app(app, url_prefix='/notifications')