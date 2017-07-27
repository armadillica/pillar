import json

from rauth import OAuth2Service
from flask import current_app, url_for, request, redirect


class OAuthSignIn(object):
    providers = None

    def __init__(self, provider_name):
        self.provider_name = provider_name
        credentials = current_app.config['OAUTH_CREDENTIALS'][provider_name]
        self.consumer_id = credentials['id']
        self.consumer_secret = credentials['secret']

    def authorize(self):
        pass

    def callback(self):
        pass

    def get_callback_url(self):
        return url_for('users.oauth_callback', provider=self.provider_name,
                       _external=True)

    @classmethod
    def get_provider(cls, provider_name):
        if cls.providers is None:
            cls.providers = {}
            for provider_class in cls.__subclasses__():
                provider = provider_class()
                cls.providers[provider.provider_name] = provider
        return cls.providers[provider_name]


class BlenderIdSignIn(OAuthSignIn):
    def __init__(self):
        super(BlenderIdSignIn, self).__init__('blender-id')

        base_url = current_app.config['OAUTH_CREDENTIALS']['blender-id'].get(
            'base_url', 'https://www.blender.org/id/')

        self.service = OAuth2Service(
            name='blender-id',
            client_id=self.consumer_id,
            client_secret=self.consumer_secret,
            authorize_url='%soauth/authorize' % base_url,
            access_token_url='%soauth/token' % base_url,
            base_url='%sapi/' % base_url
        )

    def authorize(self):
        return redirect(self.service.get_authorize_url(
            scope='email',
            response_type='code',
            redirect_uri=self.get_callback_url())
        )

    def callback(self):
        def decode_json(payload):
            return json.loads(payload.decode('utf-8'))

        if 'code' not in request.args:
            return None, None, None
        oauth_session = self.service.get_auth_session(
            data={'code': request.args['code'],
                  'grant_type': 'authorization_code',
                  'redirect_uri': self.get_callback_url()},
            decoder=decode_json
        )
        
        # TODO handle exception for failed oauth or not authorized

        me = oauth_session.get('user').json()
        # TODO handle case when user chooses not to disclose en email
        return (
            me['id'],
            me.get('email'),
            oauth_session.access_token
        )


class FacebookSignIn(OAuthSignIn):
    def __init__(self):
        super(FacebookSignIn, self).__init__('facebook')
        self.service = OAuth2Service(
            name='facebook',
            client_id=self.consumer_id,
            client_secret=self.consumer_secret,
            authorize_url='https://graph.facebook.com/oauth/authorize',
            access_token_url='https://graph.facebook.com/oauth/access_token',
            base_url='https://graph.facebook.com/'
        )

    def authorize(self):
        return redirect(self.service.get_authorize_url(
            scope='email',
            response_type='code',
            redirect_uri=self.get_callback_url())
        )

    def callback(self):
        def decode_json(payload):
            return json.loads(payload.decode('utf-8'))

        if 'code' not in request.args:
            return None, None, None
        oauth_session = self.service.get_auth_session(
            data={'code': request.args['code'],
                  'grant_type': 'authorization_code',
                  'redirect_uri': self.get_callback_url()},
            decoder=decode_json
        )
        me = oauth_session.get('me?fields=id,email').json()
        # TODO handle case when user chooses not to disclose en email
        return (
            me['id'],
            me.get('email'),
            None
        )


class GoogleSignIn(OAuthSignIn):
    def __init__(self):
        super(GoogleSignIn, self).__init__('google')
        self.service = OAuth2Service(
            name='google',
            client_id=self.consumer_id,
            client_secret=self.consumer_secret,
            authorize_url='https://accounts.google.com/o/oauth2/auth',
            access_token_url='https://accounts.google.com/o/oauth2/token',
            base_url='https://www.googleapis.com/oauth2/v1/'
        )

    def authorize(self):
        return redirect(self.service.get_authorize_url(
            scope='https://www.googleapis.com/auth/userinfo.email',
            response_type='code',
            redirect_uri=self.get_callback_url())
        )

    def callback(self):
        def decode_json(payload):
            return json.loads(payload.decode('utf-8'))

        if 'code' not in request.args:
            return None, None, None
        oauth_session = self.service.get_auth_session(
            data={'code': request.args['code'],
                  'grant_type': 'authorization_code',
                  'redirect_uri': self.get_callback_url()},
            decoder=decode_json
        )
        me = oauth_session.get('userinfo').json()
        # TODO handle case when user chooses not to disclose en email
        return (
            me['id'],
            me.get('email'),
            None
        )
