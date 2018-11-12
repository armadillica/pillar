def setup_app(app):
    from . import encoding, blender_id, projects, local_auth, file_storage
    from . import users, nodes, latest, blender_cloud, service, activities, timeline
    from . import organizations
    from . import search

    encoding.setup_app(app, url_prefix='/encoding')
    blender_id.setup_app(app, url_prefix='/blender_id')
    search.setup_app(app, url_prefix='/newsearch')
    projects.setup_app(app, api_prefix='/p')
    local_auth.setup_app(app, url_prefix='/auth')
    file_storage.setup_app(app, url_prefix='/storage')
    latest.setup_app(app, url_prefix='/latest')
    timeline.setup_app(app, url_prefix='/timeline')
    blender_cloud.setup_app(app, url_prefix='/bcloud')
    users.setup_app(app, api_prefix='/users')
    service.setup_app(app, api_prefix='/service')
    nodes.setup_app(app, url_prefix='/nodes')
    activities.setup_app(app)
    organizations.setup_app(app)
