import hashlib
import urllib


def gravatar(email, size=64):
    parameters = {'s': str(size), 'd': 'mm'}
    return "https://www.gravatar.com/avatar/" + \
        hashlib.md5(str(email)).hexdigest() + \
        "?" + urllib.urlencode(parameters)

