"""Deferred email support.

Note that this module can only be imported when an application context is
active. Best to late-import this in the functions where it's needed.
"""
from email.message import EmailMessage
from email.headerregistry import Address
import logging
import smtplib

import celery

from pillar import current_app

log = logging.getLogger(__name__)


@current_app.celery.task(bind=True, ignore_result=True, acks_late=True)
def send_email(self: celery.Task, to_name: str, to_addr: str, subject: str, text: str, html: str):
    """Send an email to a single address."""
    # WARNING: when changing the signature of this function, also change the
    # self.retry() call below.
    cfg = current_app.config

    # Construct the message
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = Address(cfg['MAIL_DEFAULT_FROM_NAME'], addr_spec=cfg['MAIL_DEFAULT_FROM_ADDR'])
    msg['To'] = (Address(to_name, addr_spec=to_addr),)
    msg.set_content(text)
    msg.add_alternative(html, subtype='html')

    # Refuse to send mail when we're testing.
    if cfg['TESTING']:
        log.warning('not sending mail to %s <%s> because we are TESTING', to_name, to_addr)
        return
    log.info('sending email to %s <%s>', to_name, to_addr)

    # Send the message via local SMTP server.
    try:
        with smtplib.SMTP(cfg['SMTP_HOST'], cfg['SMTP_PORT'], timeout=cfg['SMTP_TIMEOUT']) as smtp:
            if cfg.get('SMTP_USERNAME') and cfg.get('SMTP_PASSWORD'):
                smtp.login(cfg['SMTP_USERNAME'], cfg['SMTP_PASSWORD'])
            smtp.send_message(msg)
    except (IOError, OSError) as ex:
        log.exception('error sending email to %s <%s>, will retry later: %s',
                      to_name, to_addr, ex)
        self.retry((to_name, to_addr, subject, text, html), countdown=cfg['MAIL_RETRY'])
    else:
        log.info('mail to %s <%s> successfully sent', to_name, to_addr)
