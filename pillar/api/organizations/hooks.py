import werkzeug.exceptions as wz_exceptions

from pillar.api.utils.authentication import current_user


def pre_get_organizations(request, lookup):
    user = current_user()
    if user.is_anonymous:
        raise wz_exceptions.Forbidden()

    if user.has_cap('admin'):
        # Allow all lookups to admins.
        return

    # Only allow users to see their own organizations.
    lookup['$or'] = [{'admin_uid': user.user_id}, {'members': user.user_id}]


def pre_post_organizations(request):
    user = current_user()
    if not user.has_cap('create-organization'):
        raise wz_exceptions.Forbidden()


def setup_app(app):
    app.on_pre_GET_organizations += pre_get_organizations
    app.on_pre_POST_organizations += pre_post_organizations
