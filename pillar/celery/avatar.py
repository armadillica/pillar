"""Avatar synchronisation.

Note that this module can only be imported when an application context is
active. Best to late-import this in the functions where it's needed.
"""
import logging

from bson import ObjectId
import celery

from pillar import current_app
from pillar.api.users.avatar import sync_avatar

log = logging.getLogger(__name__)


@current_app.celery.task(bind=True, ignore_result=True, acks_late=True)
def sync_avatar_for_user(self: celery.Task, user_id: str):
    """Downloads the user's avatar from Blender ID."""
    # WARNING: when changing the signature of this function, also change the
    # self.retry() call below.

    uid = ObjectId(user_id)

    try:
        sync_avatar(uid)
    except (IOError, OSError):
        log.exception('Error downloading Blender ID avatar for user %s, will retry later')
        self.retry((user_id, ), countdown=current_app.config['AVATAR_DOWNLOAD_CELERY_RETRY'])
