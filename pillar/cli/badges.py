import datetime
import logging

from flask_script import Manager
from pillar import current_app, badge_sync
from pillar.api.utils import utcnow

log = logging.getLogger(__name__)

manager = Manager(current_app, usage="Badge operations")


@manager.option('-u', '--user', dest='email', default='', help='Email address of the user to sync')
@manager.option('-a', '--all', dest='sync_all', action='store_true', default=False,
                help='Sync all users')
@manager.option('--go', action='store_true', default=False,
                help='Actually perform the sync; otherwise it is a dry-run.')
def sync(email: str = '', sync_all: bool=False, go: bool=False):
    if bool(email) == bool(sync_all):
        raise ValueError('Use either --user or --all.')

    if email:
        users_coll = current_app.db('users')
        db_user = users_coll.find_one({'email': email}, projection={'_id': True})
        if not db_user:
            raise ValueError(f'No user with email {email!r} found')
        specific_user = db_user['_id']
    else:
        specific_user = None

    if not go:
        log.info('Performing dry-run, not going to change the user database.')
    start_time = utcnow()
    badge_sync.refresh_all_badges(specific_user, dry_run=not go,
                                  timelimit=datetime.timedelta(hours=1))
    end_time = utcnow()
    log.info('%s took %s (H:MM:SS)',
             'Updating user badges' if go else 'Dry-run',
             end_time - start_time)
