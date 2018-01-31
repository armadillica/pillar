from . import hooks
from .routes import blueprint_api


def setup_app(app, api_prefix):
    from . import patch
    patch.setup_app(app)

    app.on_replace_projects += hooks.override_is_private_field
    app.on_replace_projects += hooks.before_edit_check_permissions
    app.on_replace_projects += hooks.protect_sensitive_fields

    app.on_update_projects += hooks.override_is_private_field
    app.on_update_projects += hooks.before_edit_check_permissions
    app.on_update_projects += hooks.protect_sensitive_fields

    app.on_delete_item_projects += hooks.before_delete_project
    app.on_deleted_item_projects += hooks.after_delete_project

    app.on_insert_projects += hooks.before_inserting_override_is_private_field
    app.on_insert_projects += hooks.before_inserting_projects
    app.on_inserted_projects += hooks.after_inserting_projects

    app.on_fetched_item_projects += hooks.before_returning_project_permissions
    app.on_fetched_resource_projects += hooks.before_returning_project_resource_permissions
    app.on_fetched_item_projects += hooks.project_node_type_has_method
    app.on_fetched_resource_projects += hooks.projects_node_type_has_method

    app.register_api_blueprint(blueprint_api, url_prefix=api_prefix)
