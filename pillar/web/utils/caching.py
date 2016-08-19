import functools
from flask import g


def cache_for_request():
    """Decorator; caches the return value for the duration of the current request.

    The caller determines the cache key: *args are used as cache key, **kwargs
    are not.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not hasattr(g, 'request_level_cache'):
                g.request_level_cache = {}

            try:
                return g.request_level_cache[args]
            except KeyError:
                val = func(*args, **kwargs)
                g.request_level_cache[args] = val
                return val
        return wrapper
    return decorator
