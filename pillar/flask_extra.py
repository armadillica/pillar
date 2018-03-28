import re
import functools

import flask
import werkzeug.routing


class HashedPathConverter(werkzeug.routing.PathConverter):
    """Allows for files `xxx.yyy.js` to be served as `xxx.yyy.abc123.js`.

    The hash code is placed before the last extension.
    """
    weight = 300
    # Hash length is hard-coded to 8 characters for now.
    hash_re = re.compile(r'\.([a-zA-Z0-9]{8})(?=\.[^.]+$)')

    @functools.lru_cache(maxsize=1024)
    def to_python(self, from_url: str) -> str:
        return self.hash_re.sub('', from_url)

    @functools.lru_cache(maxsize=1024)
    def to_url(self, filepath: str) -> str:
        try:
            dotidx = filepath.rindex('.')
        except ValueError:
            # Happens when there is no dot. Very unlikely.
            return filepath

        current_hash = flask.current_app.config['STATIC_FILE_HASH']
        before, after = filepath[:dotidx], filepath[dotidx:]
        return f'{before}.{current_hash}{after}'


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
