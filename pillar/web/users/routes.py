import logging

from flask import abort, Blueprint, redirect, render_template, request, session, \
    url_for
from flask_login import login_required
from werkzeug import exceptions as wz_exceptions

from pillar import current_app
import pillar.api.blender_cloud.subscription
import pillar.auth
from pillar.api.blender_cloud.subscription import update_subscription
from pillar.api.local_auth import generate_and_store_token, get_local_user
from pillar.api.utils.authentication import find_user_in_db, upsert_user
from pillar.auth import current_user
from pillar.auth.oauth import OAuthSignIn, ProviderConfigurationMissing, ProviderNotImplemented, \
    OAuthCodeNotProvided
from pillar.web import system_util
from pillarsdk import exceptions as sdk_exceptions
from pillarsdk.users import User

from . import forms

log = logging.getLogger(__name__)
blueprint = Blueprint('users', __name__)


def check_oauth_provider(provider):
    if not provider:
        return abort(404)


@blueprint.route('/authorize/<provider>')
def oauth_authorize(provider):
    if current_user.is_authenticated:
        next_after_login = session.pop('next_after_login', None) or url_for('main.homepage')
        log.debug('Redirecting user to %s', next_after_login)
        return redirect(next_after_login)

    try:
        oauth = OAuthSignIn.get_provider(provider)
    except ProviderConfigurationMissing as e:
        log.error('Login with OAuth failed: %s', e)
        raise wz_exceptions.NotFound()
    except ProviderNotImplemented as e:
        log.error('Login with OAuth failed: %s', e)
        raise wz_exceptions.NotFound()

    return oauth.authorize()


@blueprint.route('/oauth/<provider>/authorized')
def oauth_callback(provider):
    import datetime
    from pillar.api.utils.authentication import store_token
    from pillar.api.utils import utcnow

    next_after_login = session.pop('next_after_login', None) or url_for('main.homepage')
    if current_user.is_authenticated:
        log.debug('Redirecting user to %s', next_after_login)
        return redirect(next_after_login)

    oauth = OAuthSignIn.get_provider(provider)
    try:
        oauth_user = oauth.callback()
    except OAuthCodeNotProvided as e:
        log.error(e)
        raise wz_exceptions.Forbidden()
    if oauth_user.id is None:
        log.debug('Authentication failed for user with {}'.format(provider))
        return redirect(next_after_login)

    # Find or create user
    user_info = {'id': oauth_user.id, 'email': oauth_user.email, 'full_name': ''}
    db_user = find_user_in_db(user_info, provider=provider)
    if '_deleted' in db_user and db_user['_deleted'] is True:
        log.debug('User has been deleted and will not be logge in')
        return redirect(next_after_login)
    db_id, status = upsert_user(db_user)

    # TODO(Sybren): If the user doesn't have any badges, but the access token
    # does have 'badge' scope, we should fetch the badges in the background.

    if oauth_user.access_token:
        # TODO(Sybren): make nr of days configurable, or get from OAuthSignIn subclass.
        token_expiry = utcnow() + datetime.timedelta(days=15)
        token = store_token(db_id, oauth_user.access_token, token_expiry,
                            oauth_scopes=oauth_user.scopes)
    else:
        token = generate_and_store_token(db_id)

    # Login user
    pillar.auth.login_user(token['token'], load_from_db=True)

    if provider == 'blender-id' and current_user.is_authenticated:
        # Check with Blender ID to update certain user roles.
        update_subscription()

    log.debug('Redirecting user to %s', next_after_login)
    return redirect(next_after_login)


@blueprint.route('/login')
def login():
    if request.args.get('force'):
        log.debug('Forcing logout of user before rendering login page.')
        pillar.auth.logout_user()

    session['next_after_login'] = request.args.get('next') or request.referrer
    return render_template('login.html')


@blueprint.route('/login/local', methods=['GET', 'POST'])
def login_local():
    """Login with a local account, as an alternative to OAuth.

    This provides access only to the web application."""
    form = forms.UserLoginForm()
    # Forward credentials to server
    if form.validate_on_submit():
        user = get_local_user(form.username.data, form.password.data)
        token = generate_and_store_token(user['_id'])
        pillar.auth.login_user(token['token'])
        return redirect(url_for('main.homepage'))
    return render_template('users/login.html', form=form)


@blueprint.route('/logout')
def logout():
    pillar.auth.logout_user()
    return redirect('/')


@blueprint.route('/switch')
def switch():
    from pillar.api import blender_id

    # Without this URL, the Cloud will redirect to the HTTP Referrer, which is the Blender ID
    # 'switch user' page. We need to explicitly send the user to the homepage to prevent this.
    next_url_after_cloud_login = url_for('main.homepage')

    # Without this URL, the user will remain on the Blender ID site. We want them to come
    # back to the Cloud after switching users.
    scheme = current_app.config.get('PREFERRED_URL_SCHEME', 'https')
    next_url_after_bid_login = url_for('users.login',
                                       next=next_url_after_cloud_login,
                                       force='yes',
                                       _scheme=scheme,
                                       _external=True)

    return redirect(blender_id.switch_user_url(next_url=next_url_after_bid_login))


@blueprint.route('/u/<user_id>/edit', methods=['GET', 'POST'])
@login_required
def users_edit(user_id):
    from pillar.auth import UserClass

    if not current_user.has_cap('admin'):
        return abort(403)
    api = system_util.pillar_api()

    try:
        user = User.find(user_id, api=api)
    except sdk_exceptions.ResourceNotFound:
        log.warning('Non-existing user %r requested.', user_id)
        raise wz_exceptions.NotFound('Non-existing user %r requested.' % user_id)

    form = forms.UserEditForm()
    if form.validate_on_submit():
        _users_edit(form, user, api)
    else:
        form.roles.data = user.roles
        form.email.data = user.email

    user_ob = UserClass.construct('', db_user=user.to_dict())
    return render_template('users/edit_embed.html', user=user_ob, form=form)


def _users_edit(form, user, api):
    """Performs the actual user editing."""

    from pillar.api.service import role_to_group_id

    current_user_roles = set(user.roles or [])
    current_user_groups = set(user.groups or [])

    roles_in_form = set(form.roles.data)

    granted_roles = roles_in_form - current_user_roles
    revoked_roles = forms.RolesField.form_roles() - roles_in_form

    # role_to_group_id contains ObjectIDs, but the SDK works with strings.
    granted_groups = {str(role_to_group_id[role])
                      for role in granted_roles
                      if role in role_to_group_id}
    revoked_groups = {str(role_to_group_id[role])
                      for role in revoked_roles
                      if role in role_to_group_id}

    user.roles = list((current_user_roles - revoked_roles).union(granted_roles))
    user.groups = list((current_user_groups - revoked_groups).union(granted_groups))
    user.email = form.email.data

    user.update(api=api)


@blueprint.route('/u')
@login_required
def users_index():
    if not current_user.has_role('admin'):
        return abort(403)
    return render_template('users/index.html')


