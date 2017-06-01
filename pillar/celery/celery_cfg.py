from celery import Celery

task_modules = [
    'pillar.celery.tasks',
]

celery_cfg = Celery('proj',
                    backend='redis://redis/1',
                    broker='amqp://guest:guest@rabbit//',
                    include=task_modules,
                    task_track_started=True)

# Optional configuration, see the application user guide.
celery_cfg.conf.update(
    result_expires=3600,
)

if __name__ == '__main__':
    celery_cfg.start()
