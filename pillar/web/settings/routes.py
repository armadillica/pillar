import json
import logging

from flask import Blueprint, flash, render_template
from flask_login import login_required, current_user
from werkzeug.exceptions import abort

from pillar.web import system_util
from pillar.web.users import forms
from pillarsdk import User, exceptions as sdk_exceptions

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
            user.username = form.username.data
            user.update(api=api)
            flash("Profile updated", 'success')
        except sdk_exceptions.ResourceInvalid as e:
            message = json.loads(e.content)
            flash(message)

    return render_template('users/settings/profile.html', form=form, title='profile')


@blueprint.route('/roles')
@login_required
def roles():
    """Show roles and capabilties of the current user."""
    return render_template('users/settings/roles.html', title='roles')
