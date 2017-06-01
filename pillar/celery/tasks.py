import logging
import typing

from .celery_cfg import celery_cfg

log = logging.getLogger(__name__)


@celery_cfg.task(track_started=True)
def long_task(numbers: typing.List[int]):
    _log = log.getChild('long_task')
    _log.info('Computing sum of %i items', len(numbers))

    import time
    time.sleep(6)
    thesum = sum(numbers)

    _log.info('Computed sum of %i items', len(numbers))

    return thesum

