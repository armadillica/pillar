"""Badge HTML synchronisation.

Note that this module can only be imported when an application context is
active. Best to late-import this in the functions where it's needed.
"""
import datetime
import logging

from pillar import current_app, badge_sync

log = logging.getLogger(__name__)


@current_app.celery.task(ignore_result=True)
def sync_badges_for_users(timelimit_seconds: int):
    """Synchronises Blender ID badges for the most-urgent users."""

    timelimit = datetime.timedelta(seconds=timelimit_seconds)
    log.info('Refreshing badges, timelimit is %s (H:MM:SS)', timelimit)
    badge_sync.refresh_all_badges(timelimit=timelimit)
