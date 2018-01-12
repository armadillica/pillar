import functools
import flask


def add_response_headers(headers: dict):
    """This decorator adds the headers passed in to the response"""

    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            resp = flask.make_response(f(*args, **kwargs))
            h = resp.headers
            for header, value in headers.items():
                h[header] = value
            return resp

        return decorated_function

    return decorator


def vary_xhr():
    """View function decorator; adds HTTP header "Vary: X-Requested-With" to the response"""

    def decorator(f):
        header_adder = add_response_headers({'Vary': 'X-Requested-With'})
        return header_adder(f)

    return decorator


def ensure_schema(url: str) -> str:
    """Return the same URL with the configured PREFERRED_URL_SCHEME."""
    import urllib.parse

    if not url:
        return url

    bits = urllib.parse.urlsplit(url, allow_fragments=True)

    if not bits[0] and not bits[1]:
        # don't replace the schema if there is not even a hostname.
        return url

    scheme = flask.current_app.config.get('PREFERRED_URL_SCHEME', 'https')
    bits = (scheme, *bits[1:])
    return urllib.parse.urlunsplit(bits)
