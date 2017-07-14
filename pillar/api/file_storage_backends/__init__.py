"""Storage backends.

To obtain a storage backend, use either of the two forms:

>>> bucket = default_storage_backend('bucket_name')

>>> BucketClass = Bucket.for_backend('backend_name')
>>> bucket = BucketClass('bucket_name')

"""

from .abstract import Bucket

# Import the other backends so that they register.
from . import local
from . import gcs


def default_storage_backend(name: str) -> Bucket:
    """Returns an instance of a Bucket, based on the default backend.

    Depending on the backend this may actually create the bucket.
    """
    from flask import current_app

    backend_name = current_app.config['STORAGE_BACKEND']
    backend_cls = Bucket.for_backend(backend_name)

    return backend_cls(name)
