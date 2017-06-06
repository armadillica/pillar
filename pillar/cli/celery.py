import logging

from flask_script import Manager
from pillar import current_app

log = logging.getLogger(__name__)

manager_celery = Manager(
    current_app, usage="Celery operations, like starting a worker or showing the queue")


@manager_celery.option('args', nargs='*')
def worker(args):
    """Runs a Celery worker."""

    import sys

    argv0 = f'{sys.argv[0]} operations worker'
    argvother = [
        '-E',
        '-l', 'INFO',
        '--concurrency', '1',
        '--pool', 'solo',  # No preforking, as PyMongo can't handle connect-before-fork.
                           # We might get rid of this and go for the default Celery worker
                           # preforking concurrency model, *if* we can somehow reset the
                           # PyMongo client and reconnect after forking.
    ] + list(args)

    current_app.celery.worker_main([argv0] + argvother)


@manager_celery.command
def queue():
    """Shows queued Celery tasks."""

    from pprint import pprint

    # Inspect all nodes.
    i = current_app.celery.control.inspect()

    print(50 * '=')
    print('Tasks that have an ETA or are scheduled for later processing:')
    pprint(i.scheduled())

    print()
    print('Tasks that are currently active:')
    pprint(i.active())

    print()
    print('Tasks that have been claimed by workers:')
    pprint(i.reserved())
    print(50 * '=')


@manager_celery.command
def purge():
    """Deletes queued Celery tasks."""

    log.warning('Purging all pending Celery tasks.')
    current_app.celery.control.purge()
