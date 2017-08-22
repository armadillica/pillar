import logging
import typing

from flask import current_app, Blueprint

from pillar.api.utils import authorization

log = logging.getLogger(__name__)
blueprint = Blueprint('blender_cloud.subscription', __name__)


def fetch_subscription_info(email: str) -> typing.Optional[dict]:
    """Returns the user info dict from the external subscriptions management server.

    :returns: the store user info, or None if the user can't be found or there
        was an error communicating. A dict like this is returned:
        {
            "shop_id": 700,
            "cloud_access": 1,
            "paid_balance": 314.75,
            "balance_currency": "EUR",
            "start_date": "2014-08-25 17:05:46",
            "expiration_date": "2016-08-24 13:38:45",
            "subscription_status": "wc-active",
            "expiration_date_approximate": true
        }
    """

    import requests
    from requests.adapters import HTTPAdapter
    import requests.exceptions

    external_subscriptions_server = current_app.config['EXTERNAL_SUBSCRIPTIONS_MANAGEMENT_SERVER']

    if log.isEnabledFor(logging.DEBUG):
        import urllib.parse

        log_email = urllib.parse.quote(email)
        log.debug('Connecting to store at %s?blenderid=%s',
                  external_subscriptions_server, log_email)

    # Retry a few times when contacting the store.
    s = requests.Session()
    s.mount(external_subscriptions_server, HTTPAdapter(max_retries=5))

    try:
        r = s.get(external_subscriptions_server,
                  params={'blenderid': email},
                  verify=current_app.config['TLS_CERT_FILE'],
                  timeout=current_app.config.get('EXTERNAL_SUBSCRIPTIONS_TIMEOUT_SECS', 10))
    except requests.exceptions.ConnectionError as ex:
        log.error('Error connecting to %s: %s', external_subscriptions_server, ex)
        return None
    except requests.exceptions.Timeout as ex:
        log.error('Timeout communicating with %s: %s', external_subscriptions_server, ex)
        return None
    except requests.exceptions.RequestException as ex:
        log.error('Some error communicating with %s: %s', external_subscriptions_server, ex)
        return None

    if r.status_code != 200:
        log.warning("Error communicating with %s, code=%i, unable to check "
                    "subscription status of user %s",
                    external_subscriptions_server, r.status_code, email)
        return None

    store_user = r.json()

    if log.isEnabledFor(logging.DEBUG):
        import json
        log.debug('Received JSON from store API: %s',
                  json.dumps(store_user, sort_keys=False, indent=4))

    return store_user


@blueprint.route('/update-subscription')
@authorization.require_login()
def update_subscription():
    """Updates the subscription status of the current user.

    Returns an empty HTTP response.
    """

    import pprint
    from pillar.api import blender_id, service
    from pillar.api.utils import authentication

    my_log: logging.Logger = log.getChild('update_subscription')
    user_id = authentication.current_user_id()

    bid_user = blender_id.fetch_blenderid_user()
    if not bid_user:
        my_log.warning('Logged in user %s has no BlenderID account! '
                       'Unable to update subscription status.', user_id)
        return '', 204

    # Use the Blender ID email address to check with the store. At least that reduces the
    # number of email addresses that could be out of sync to two (rather than three when we
    # use the email address from our local database).
    try:
        email = bid_user['email']
    except KeyError:
        my_log.error('Blender ID response did not include an email address, '
                     'unable to update subscription status: %s',
                     pprint.pformat(bid_user, compact=True))
        return 'Internal error', 500
    store_user = fetch_subscription_info(email) or {}

    # Handle the role changes via the badger service functionality.
    grant_subscriber = store_user.get('cloud_access', 0) == 1
    grant_demo = bid_user.get('roles', {}).get('cloud_demo', False)

    is_subscriber = authorization.user_has_role('subscriber')
    is_demo = authorization.user_has_role('demo')

    if grant_subscriber != is_subscriber:
        action = 'grant' if grant_subscriber else 'revoke'
        my_log.info('%sing subscriber role to user %s (Blender ID email %s)',
                    action, user_id, email)
        service.do_badger(action, role='subscriber', user_id=user_id)
    else:
        my_log.debug('Not changing subscriber role, grant=%r and is=%s',
                     grant_subscriber, is_subscriber)

    if grant_demo != is_demo:
        action = 'grant' if grant_demo else 'revoke'
        my_log.info('%sing demo role to user %s (Blender ID email %s)', action, user_id, email)
        service.do_badger(action, role='demo', user_id=user_id)
    else:
        my_log.debug('Not changing demo role, grant=%r and is=%s',
                     grant_demo, is_demo)

    return '', 204


def setup_app(app, url_prefix):
    log.info('Registering blueprint at %s', url_prefix)
    app.register_api_blueprint(blueprint, url_prefix=url_prefix)
