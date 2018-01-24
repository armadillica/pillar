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


def on_fetched_item_organizations(org_doc: dict):
    """Filter out binary data.

    Eve cannot return binary data, at least not until we upgrade to a version
    that depends on Cerberus >= 1.0.
    """

    for ipr in org_doc.get('ip_ranges') or []:
        ipr.pop('start', None)
        ipr.pop('end', None)
        ipr.pop('prefix', None)  # not binary, but useless without the other fields.


def on_fetched_resource_organizations(response: dict):
    for org_doc in response.get('_items', []):
        on_fetched_item_organizations(org_doc)


def pre_post_organizations(request):
    user = current_user()
    if not user.has_cap('create-organization'):
        raise wz_exceptions.Forbidden()


def setup_app(app):
    app.on_pre_GET_organizations += pre_get_organizations
    app.on_pre_POST_organizations += pre_post_organizations

    app.on_fetched_item_organizations += on_fetched_item_organizations
    app.on_fetched_resource_organizations += on_fetched_resource_organizations
