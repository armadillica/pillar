from flask_login import current_user
from flask_wtf import Form
from pillar.web import system_util
from pillarsdk.users import User

from wtforms import BooleanField
from wtforms import PasswordField
from wtforms import RadioField
from wtforms import SelectMultipleField
from wtforms import StringField
from wtforms.validators import DataRequired
from wtforms.validators import Length
from wtforms.validators import Regexp
import wtforms.validators as wtvalid


class UserLoginForm(Form):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')

    def __init__(self, csrf_enabled=False, *args, **kwargs):
        super(UserLoginForm, self).__init__(csrf_enabled=False, *args, **kwargs)


class UserProfileForm(Form):
    username = StringField('Username', validators=[DataRequired(), Length(
        min=3, max=128, message="Min. 3, max. 128 chars please"), Regexp(
        r'^[\w.@+-]+$', message="Please do not use spaces")])

    def __init__(self, csrf_enabled=False, *args, **kwargs):
        super().__init__(csrf_enabled=csrf_enabled, *args, **kwargs)
        self.user = None

    def validate(self):
        rv = super().validate()
        if not rv:
            return False

        api = system_util.pillar_api()
        user = User.find(current_user.objectid, api=api)
        if user.username != self.username.data:
            username = User.find_first(
                {'where': {"username": self.username.data}},
                api=api)

            if username:
                self.username.errors.append('Sorry, this username is already taken.')
                return False

        self.user = user
        return True


class UserSettingsEmailsForm(Form):
    choices = [
        (1, 'Keep me updated with Blender Cloud news.'),
        (0, 'Do not mail me news update.')]
    email_communications = RadioField(
        'Notifications', choices=choices, coerce=int)


class RolesField(SelectMultipleField):
    def __init__(self, label=None, validators=None, coerce=str, **kwargs):
        role_choices = [(r, r) for r in sorted(self.form_roles())]
        super().__init__(label=label, validators=validators, coerce=coerce,
                         choices=role_choices, **kwargs)

    @classmethod
    def form_roles(cls) -> set:
        """Returns the set of roles used in this form."""

        from pillar import current_app
        return current_app.user_roles


class UserEditForm(Form):
    roles = RolesField('Roles')
    email = StringField(
        validators=[wtvalid.DataRequired(), wtvalid.Email()],
        description='Make sure this matches the Store and Blender ID email address.'
    )
