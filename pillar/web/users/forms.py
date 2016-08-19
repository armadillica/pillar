from flask.ext.login import current_user
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


class UserLoginForm(Form):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')

    def __init__(self, csrf_enabled=False, *args, **kwargs):
        super(UserLoginForm, self).__init__(csrf_enabled=False, *args, **kwargs)


class UserProfileForm(Form):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(
        min=3, max=128, message="Min. 3 and max. 128 chars please")])
    username = StringField('Username', validators=[DataRequired(), Length(
        min=3, max=128, message="Min. 3, max. 128 chars please"), Regexp(
        r'^[\w.@+-]+$', message="Please do not use spaces")])

    def __init__(self, csrf_enabled=False, *args, **kwargs):
        super(UserProfileForm, self).__init__(csrf_enabled=False, *args, **kwargs)

    def validate(self):
        rv = Form.validate(self)
        if not rv:
            return False

        api = system_util.pillar_api()
        user = User.find(current_user.objectid, api=api)
        if user.username != self.username.data:
            username = User.find_first(
                {'where': '{"username": "%s"}' % self.username.data},
                api=api)

            if username:
                self.username.errors.append('Sorry, username already exists!')
                return False

        self.user = user
        return True


class UserSettingsEmailsForm(Form):
    choices = [
        (1, 'Keep me updated with Blender Cloud news.'),
        (0, 'Do not mail me news update.')]
    email_communications = RadioField(
        'Notifications', choices=choices, coerce=int)


class UserEditForm(Form):
    role_choices = [('admin', 'admin'),
                    ('subscriber', 'subscriber'),
                    ('demo', 'demo')]
    roles = SelectMultipleField('Roles', choices=role_choices)
