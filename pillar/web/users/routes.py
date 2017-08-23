import json
import logging

from werkzeug import exceptions as wz_exceptions
from flask import abort, Blueprint, current_app, flash, redirect, render_template, request, session,\
    url_for
from flask_login import login_required, logout_user, current_user

from pillarsdk import exceptions as sdk_exceptions
from pillarsdk.users import User
from pillarsdk.groups import Group
import pillar.api.blender_cloud.subscription
import pillar.auth
from pillar.web import system_util
from pillar.api.local_auth import generate_and_store_token, get_local_user
from pillar.api.utils.authentication import find_user_in_db, upsert_user
from pillar.api.blender_cloud.subscription import update_subscription
from pillar.auth.oauth import OAuthSignIn
from . import forms

log = logging.getLogger(__name__)
blueprint = Blueprint('users', __name__)


def check_oauth_provider(provider):
    if not provider:
        return abort(404)


@blueprint.route('/authorize/<provider>')
def oauth_authorize(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('main.homepage'))
    oauth = OAuthSignIn.get_provider(provider)
    return oauth.authorize()


@blueprint.route('/oauth/<provider>/authorized')
def oauth_callback(provider):
    if not current_user.is_anonymous:
        return redirect(url_for('main.homepage'))
    oauth = OAuthSignIn.get_provider(provider)
    oauth_user = oauth.callback()
    if oauth_user.id is None:
        log.debug('Authentication failed for user with {}'.format(provider))
        return redirect(url_for('main.homepage'))

    # Find or create user
    user_info = {'id': oauth_user.id, 'email': oauth_user.email, 'full_name': ''}
    db_user = find_user_in_db(user_info, provider=provider)
    db_id, status = upsert_user(db_user)
    token = generate_and_store_token(db_id)

    # Login user
    pillar.auth.login_user(token['token'], load_from_db=True)

    if provider == 'blender-id' and current_user is not None:
        # Check with the store for user roles. If the user has an active subscription, we apply
        # the 'subscriber' role
        update_subscription()

    next_after_login = session.pop('next_after_login', None)
    if next_after_login:
        log.debug('Redirecting user to %s', next_after_login)
        return redirect(next_after_login)
    return redirect(url_for('main.homepage'))


@blueprint.route('/login')
def login():
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
    logout_user()
    session.clear()
    return redirect('/')


@blueprint.route('/switch')
def switch():
    from pillar.api import blender_id

    # Without this URL, the Cloud will redirect to the HTTP Referrer, which is the Blender ID
    # 'switch user' page. We need to explicitly send the user to the homepage to prevent this.
    next_url_after_cloud_login = url_for('main.homepage')

    # Without this URL, the user will remain on the Blender ID site. We want them to come
    # back to the Cloud after switching users.
    next_url_after_bid_login = url_for('users.login',
                                       next=next_url_after_cloud_login,
                                       _external=True)

    return redirect(blender_id.switch_user_url(next_url=next_url_after_bid_login))


@blueprint.route('/settings/profile', methods=['GET', 'POST'])
@login_required
def settings_profile():
    """Profile view and edit page. This is a temporary implementation.
    """
    if current_user.has_role('protected'):
        return abort(404)  # TODO: make this 403, handle template properly
    api = system_util.pillar_api()
    user = User.find(current_user.objectid, api=api)

    form = forms.UserProfileForm(
        full_name=user.full_name,
        username=user.username)

    if form.validate_on_submit():
        try:
            user.full_name = form.full_name.data
            user.username = form.username.data
            user.update(api=api)
            flash("Profile updated", 'success')
        except sdk_exceptions.ResourceInvalid as e:
            message = json.loads(e.content)
            flash(message)

    return render_template('users/settings/profile.html', form=form, title='profile')


@blueprint.route('/settings/emails', methods=['GET', 'POST'])
@login_required
def settings_emails():
    """Main email settings.
    """
    if current_user.has_role('protected'):
        return abort(404)  # TODO: make this 403, handle template properly
    api = system_util.pillar_api()
    user = User.find(current_user.objectid, api=api)

    # Force creation of settings for the user (safely remove this code once
    # implemented on account creation level, and after adding settings to all
    # existing users)
    if not user.settings:
        user.settings = dict(email_communications=1)
        user.update(api=api)

    if user.settings.email_communications is None:
        user.settings.email_communications = 1
        user.update(api=api)

    # Generate form
    form = forms.UserSettingsEmailsForm(
        email_communications=user.settings.email_communications)

    if form.validate_on_submit():
        try:
            user.settings.email_communications = form.email_communications.data
            user.update(api=api)
            flash("Profile updated", 'success')
        except sdk_exceptions.ResourceInvalid as e:
            message = json.loads(e.content)
            flash(message)

    return render_template('users/settings/emails.html', form=form, title='emails')


@blueprint.route('/settings/billing')
@login_required
def settings_billing():
    """View the subscription status of a user
    """
    if current_user.has_role('protected'):
        return abort(404)  # TODO: make this 403, handle template properly
    api = system_util.pillar_api()
    user = User.find(current_user.objectid, api=api)
    groups = []
    if user.groups:
        for group_id in user.groups:
            group = Group.find(group_id, api=api)
            groups.append(group.name)

    store_user = pillar.api.blender_cloud.subscription.fetch_subscription_info(user.email)

    return render_template(
        'users/settings/billing.html',
        store_user=store_user, groups=groups, title='billing')


@blueprint.route('/u/<user_id>/edit', methods=['GET', 'POST'])
@login_required
def users_edit(user_id):
    from pillar.auth import UserClass

    if not current_user.has_role('admin'):
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
