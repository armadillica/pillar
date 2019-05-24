import json
import logging
import urllib.parse

from flask import Blueprint, flash, render_template
from flask_login import login_required
from werkzeug.exceptions import abort

from pillar import current_app
from pillar.api.utils import jsonify
import pillar.api.users.avatar
from pillar.auth import current_user
from pillar.web import system_util
from pillar.web.users import forms
from pillarsdk import File, User, exceptions as sdk_exceptions

log = logging.getLogger(__name__)
blueprint = Blueprint('settings', __name__)


@blueprint.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Profile view and edit page. This is a temporary implementation.
    """
    if current_user.has_role('protected'):
        return abort(404)  # TODO: make this 403, handle template properly
    api = system_util.pillar_api()
    user = User.find(current_user.objectid, api=api)

    form = forms.UserProfileForm(username=user.username)

    if form.validate_on_submit():
        try:
            response = user.set_username(form.username.data, api=api)
            log.info('updated username of %s: %s', current_user, response)
            flash("Profile updated", 'success')
        except sdk_exceptions.ResourceInvalid as ex:
            log.warning('unable to set username %s to %r: %s', current_user, form.username.data, ex)
            message = json.loads(ex.content)
            flash(message)

    blender_id_endpoint = current_app.config['BLENDER_ID_ENDPOINT']
    blender_profile_url = urllib.parse.urljoin(blender_id_endpoint, 'settings/profile')

    return render_template('users/settings/profile.html',
                           form=form, title='profile',
                           blender_profile_url=blender_profile_url)


@blueprint.route('/roles')
@login_required
def roles():
    """Show roles and capabilties of the current user."""
    return render_template('users/settings/roles.html', title='roles')


@blueprint.route('/profile/sync-avatar', methods=['POST'])
@login_required
def sync_avatar():
    """Fetch the user's avatar from Blender ID and save to storage.

    This is an API-like endpoint, in the sense that it returns JSON.
    It's here in this file to have it close to the endpoint that
    serves the only page that calls on this endpoint.
    """

    new_url = pillar.api.users.avatar.sync_avatar(current_user.user_id)
    if not new_url:
        return jsonify({'_message': 'Your avatar could not be updated'})
    return new_url
