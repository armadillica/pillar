"""Cloud subscription info.

Connects to the external subscription server to obtain user info.
"""

import logging

from flask import current_app
import requests
from requests.adapters import HTTPAdapter

log = logging.getLogger(__name__)


def fetch_user(email):
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
    :rtype: dict
    """

    external_subscriptions_server = current_app.config['EXTERNAL_SUBSCRIPTIONS_MANAGEMENT_SERVER']

    log.debug('Connecting to store at %s?blenderid=%s', external_subscriptions_server, email)

    # Retry a few times when contacting the store.
    s = requests.Session()
    s.mount(external_subscriptions_server, HTTPAdapter(max_retries=5))
    r = s.get(external_subscriptions_server, params={'blenderid': email},
              verify=current_app.config['TLS_CERT_FILE'])

    if r.status_code != 200:
        log.warning("Error communicating with %s, code=%i, unable to check "
                    "subscription status of user %s",
                    external_subscriptions_server, r.status_code, email)
        return None

    store_user = r.json()
    return store_user

