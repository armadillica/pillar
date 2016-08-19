import logging
import string
import urlparse

from flask import Blueprint, redirect, current_app
from werkzeug.exceptions import NotFound
import pillarsdk

from pillar.web import system_util
from pillar.web.nodes.routes import url_for_node

blueprint = Blueprint('redirects', __name__)
log = logging.getLogger(__name__)

short_code_chars = string.ascii_letters + string.digits


@blueprint.route('/<path:path>')
def redirect_to_path(path):
    redirects = current_app.config.get('REDIRECTS', {})

    # Try our dict of redirects first.
    try:
        url = redirects[path]
    except KeyError:
        pass
    else:
        return redirect(url, code=307)

    # The path may be a node short-code.
    resp = redirect_with_short_code(path)
    if resp is not None:
        return resp

    log.warning('Non-existing redirect %r requested', path)
    raise NotFound()


def redirect_with_short_code(short_code):
    if any(c not in short_code_chars for c in short_code):
        # Can't be a short code
        return

    log.debug('Path %s may be a short-code', short_code)

    api = system_util.pillar_api()
    try:
        node = pillarsdk.Node.find_one({'where': {'short_code': short_code},
                                        'projection': {'_id': 1}},
                                       api=api)
    except pillarsdk.ResourceNotFound:
        log.debug("Nope, it isn't.")
        return

    # Redirect to 'theatre' view for the node.
    url = url_for_node(node=node)
    url = urlparse.urljoin(url, '?t')

    log.debug('Found short code %s, redirecting to %s', short_code, url)
    return redirect(url, code=307)


def setup_app(app, url_prefix):
    app.register_blueprint(blueprint, url_prefix=url_prefix)
