"""Support for adding CORS headers to responses."""

import functools

import flask
import werkzeug.wrappers as wz_wrappers
import werkzeug.exceptions as wz_exceptions


def allow(*, allow_credentials=False):
    """Flask endpoint decorator, adds CORS headers to the response.

    If the request has a non-empty 'Origin' header, the response header
    'Access-Control-Allow-Origin' is set to the value of that request header,
    and some other CORS headers are set.
    """
    def decorator(wrapped):
        @functools.wraps(wrapped)
        def wrapper(*args, **kwargs):
            request_origin = flask.request.headers.get('Origin')
            if not request_origin:
                # No CORS headers requested, so don't bother touching the response.
                return wrapped(*args, **kwargs)

            try:
                response = wrapped(*args, **kwargs)
            except wz_exceptions.HTTPException as ex:
                response = ex.get_response()
            else:
                if isinstance(response, tuple):
                    response = flask.make_response(*response)
                elif isinstance(response, str):
                    response = flask.make_response(response)
                elif isinstance(response, wz_wrappers.Response):
                    pass
                else:
                    raise TypeError(f'unknown response type {type(response)}')

            assert isinstance(response, wz_wrappers.Response)

            response.headers.set('Access-Control-Allow-Origin', request_origin)
            response.headers.set('Access-Control-Allow-Headers', 'x-requested-with')
            if allow_credentials:
                response.headers.set('Access-Control-Allow-Credentials', 'true')

            return response
        return wrapper
    return decorator
