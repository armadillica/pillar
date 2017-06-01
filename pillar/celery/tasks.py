import logging
import typing

from pillar import current_app

log = logging.getLogger(__name__)


@current_app.celery.task(track_started=True)
def long_task(numbers: typing.List[int]):
    _log = log.getChild('long_task')
    _log.info('Computing sum of %i items', len(numbers))

    import time
    time.sleep(6)
    thesum = sum(numbers)

    _log.info('Computed sum of %i items', len(numbers))

    return thesum
