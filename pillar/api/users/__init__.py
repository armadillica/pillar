from . import hooks
from .routes import blueprint_api


def setup_app(app, api_prefix):
    app.on_pre_GET_users += hooks.check_user_access
    app.on_post_GET_users += hooks.post_GET_user
    app.on_pre_PUT_users += hooks.check_put_access
    app.on_pre_PUT_users += hooks.before_replacing_user
    app.on_replaced_users += hooks.push_updated_user_to_algolia
    app.on_replaced_users += hooks.send_blinker_signal_roles_changed
    app.on_fetched_item_users += hooks.after_fetching_user
    app.on_fetched_resource_users += hooks.after_fetching_user_resource

    app.register_api_blueprint(blueprint_api, url_prefix=api_prefix)
