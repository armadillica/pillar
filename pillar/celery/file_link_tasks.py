from pillar import current_app


@current_app.celery.task(ignore_result=True)
def regenerate_all_expired_links(backend_name: str, chunk_size: int):
    """Regenerate all expired links for all non-deleted file documents.

    Probably only works on Google Cloud Storage ('gcs') backends at
    the moment, since those are the only links that actually expire.

    :param backend_name: name of the backend to refresh for.
    :param chunk_size: the maximum number of files to refresh in this run.
    """
    from pillar.api import file_storage

    # Refresh all files that already have expired or will expire in the next
    # two hours. Since this task is intended to run every hour, this should
    # result in all regular file requests having a valid link.
    file_storage.refresh_links_for_backend(backend_name, chunk_size, expiry_seconds=7200)
