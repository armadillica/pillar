import json
import logging
import requests

from flask import (abort, Blueprint, current_app, flash, redirect,
                   render_template, request, session, url_for)
from flask_login import login_required, logout_user, current_user
from flask_oauthlib.client import OAuthException
from werkzeug import exceptions as wz_exceptions

import pillar.api.blender_cloud.subscription
import pillar.auth
from pillar.web import system_util

from . import forms

from pillarsdk import exceptions as sdk_exceptions
from pillarsdk.users import User
from pillarsdk.groups import Group

log = logging.getLogger(__name__)
blueprint = Blueprint('users', __name__)


def check_oauth_provider(provider):
    if not provider:
        return abort(404)


@blueprint.route('/login')
def login():
    check_oauth_provider(current_app.oauth_blender_id)

    session['next_after_login'] = request.args.get('next') or request.referrer

    callback = url_for(
        'users.blender_id_authorized',
        _external=True,
        _scheme=current_app.config['SCHEME']
    )
    return current_app.oauth_blender_id.authorize(callback=callback)


@blueprint.route('/oauth/blender-id/authorized')
def blender_id_authorized():
    check_oauth_provider(current_app.oauth_blender_id)
    try:
        oauth_resp = current_app.oauth_blender_id.authorized_response()
        if isinstance(oauth_resp, OAuthException):
            raise oauth_resp
    except OAuthException as ex:
        log.warning('Error parsing BlenderID OAuth response. data=%s; message=%s',
                    ex.data, ex.message)
        raise wz_exceptions.Forbidden('Access denied, sorry!')

    if oauth_resp is None:
        msg = 'Access denied: reason=%s error=%s' % (
            request.args.get('error_reason'), request.args.get('error_description'))
        log.warning('Access denied to user because oauth_resp=None: %s', msg)
        return wz_exceptions.Forbidden(msg)

    session['blender_id_oauth_token'] = (oauth_resp['access_token'], '')

    pillar.auth.login_user(oauth_resp['access_token'])

    if current_user is not None:
        # Check with the store for user roles. If the user has an active
        # subscription, we apply the 'subscriber' role
        api = system_util.pillar_api(token=oauth_resp['access_token'])
        api.get('bcloud/update-subscription')

    next_after_login = session.pop('next_after_login', None)
    if next_after_login:
        log.debug('Redirecting user to %s', next_after_login)
        return redirect(next_after_login)
    return redirect(url_for('main.homepage'))


@blueprint.route('/login/local', methods=['GET', 'POST'])
def login_local():
    """Login with a local account, skipping OAuth. This provides access only
    to the web application and is meant for limited access (for example in
    the case of a shared account)."""
    form = forms.UserLoginForm()
    # Forward credentials to server
    if form.validate_on_submit():
        payload = {
            'username': form.username.data,
            'password': form.password.data
            }
        r = requests.post("{0}auth/make-token".format(
            system_util.pillar_server_endpoint()), data=payload)
        if r.status_code != 200:
            return abort(r.status_code)
        res = r.json()
        # If correct, receive token and log in the user
        pillar.auth.login_user(res['token'])
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
    return render_template('users/edit_embed.html',
        user=user,
        form=form)


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
