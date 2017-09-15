"""PillarSDK subclass for direct Flask-internal calls."""

import logging
import urllib.parse
from flask import current_app

import pillarsdk
from pillarsdk import exceptions

log = logging.getLogger(__name__)


class FlaskInternalApi(pillarsdk.Api):
    """SDK API subclass that calls Flask directly.

    Can only be used from the same Python process the Pillar server itself is
    running on.
    """

    def http_call(self, url, method, **kwargs):
        """Fakes a http call through Flask/Werkzeug."""
        client = current_app.test_client()
        self.requests_to_flask_kwargs(kwargs)

        # Leave out the query string and fragment from the URL.
        split_url = urllib.parse.urlsplit(url)
        path = urllib.parse.urlunsplit(split_url[:-2] + (None, None))
        try:
            response = client.open(path=path, query_string=split_url.query, method=method,
                                   **kwargs)
        except Exception as ex:
            log.warning('Error performing HTTP %s request to %s: %s', method,
                        url, str(ex))
            raise

        if method == 'OPTIONS':
            return response

        self.flask_to_requests_response(response)

        try:
            content = self.handle_response(response, response.data)
        except:
            log.warning("%s: Response[%s]: %s", url, response.status_code,
                        response.data)
            raise

        return content

    def requests_to_flask_kwargs(self, kwargs):
        """Converts Requests arguments to Flask test client arguments."""

        kwargs.pop('verify', None)
        # No network connection, so nothing to verify.

        # Files to upload need to be sent in the 'data' kwarg instead of the
        # 'files' kwarg, and have a different order.
        if 'files' in kwargs:
            # By default, 'data' is there but None, so setdefault('data', {})
            # won't work.
            data = kwargs.get('data') or {}

            for file_name, file_value in kwargs['files'].items():
                fname, fobj, mimeytpe = file_value
                data[file_name] = (fobj, fname)

            del kwargs['files']
            kwargs['data'] = data

    def flask_to_requests_response(self, response):
        """Adds some properties to a Flask response object to mimick a Requests
        object.
        """

        # Our API always sends back UTF8, so we don't have to check headers for
        # that.
        if response.mimetype.startswith('text'):
            response.text = response.data.decode('utf8')
        else:
            response.text = None

    def OPTIONS(self, action, headers=None):
        """Make OPTIONS request.

        Contrary to other requests, this method returns the raw requests.Response object.

        :rtype: requests.Response
        """
        import os

        url = os.path.join(self.endpoint, action.strip('/'))
        response = self.request(url, 'OPTIONS', headers=headers)
        if 200 <= response.status_code <= 299:
            return response

        exception = exceptions.exception_for_status(response.status_code)
        text = getattr(response, 'text', '')
        if exception:
            raise exception(response, text)

        raise exceptions.ConnectionError(response, text,
                                         "Unknown response code: %s" % response.status_code)
