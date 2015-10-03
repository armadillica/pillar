import os
import time
import datetime
from gcloud.storage.client import Client
from oauth2client.client import SignedJwtAssertionCredentials
from application import app


class GoogleCloudStorageBucket(object):
    """Cloud Storage bucket interface. We create a bucket for every project. In
    the bucket we create first level subdirs as follows:
    - '_' (will contain hashed assets, and stays on top of defaul listing)
    - 'svn' (svn checkout mirror)
    - 'shared' (any additional folder of static folder that is accessed via a
      node of 'storage' node_type)

    :type bucket_name: string
    :param bucket_name: Name of the bucket.

    :type subdir: string
    :param subdir: The local entrypoint to browse the bucket.

    """

    def __init__(self, bucket_name, subdir='_/'):
        CGS_PROJECT_NAME = app.config['CGS_PROJECT_NAME']
        GCS_CLIENT_EMAIL = app.config['GCS_CLIENT_EMAIL']
        GCS_PRIVATE_KEY_PEM = app.config['GCS_PRIVATE_KEY_PEM']
        GCS_PRIVATE_KEY_P12 = app.config['GCS_PRIVATE_KEY_P12']

        # Load private key in pem format (used by the API)
        with open(GCS_PRIVATE_KEY_PEM) as f:
          private_key_pem = f.read()
        credentials_pem = SignedJwtAssertionCredentials(GCS_CLIENT_EMAIL,
            private_key_pem,
            'https://www.googleapis.com/auth/devstorage.read_write')

        # Load private key in p12 format (used by the singed urls generator)
        with open(GCS_PRIVATE_KEY_P12) as f:
          private_key_pkcs12 = f.read()
        self.credentials_p12 = SignedJwtAssertionCredentials(GCS_CLIENT_EMAIL,
            private_key_pkcs12,
            'https://www.googleapis.com/auth/devstorage.read_write')

        gcs = Client(project=CGS_PROJECT_NAME, credentials=credentials_pem)
        self.bucket = gcs.get_bucket(bucket_name)
        self.subdir = subdir

    def List(self, path=None):
        """Display the content of a subdir in the project bucket. If the path
        points to a file the listing is simply empty.

        :type path: string
        :param path: The relative path to the directory or asset.
        """
        if path and not path.endswith('/'):
            path += '/'
        prefix = os.path.join(self.subdir, path)

        fields_to_return = 'nextPageToken,items(name,size,contentType),prefixes'
        req = self.bucket.list_blobs(fields=fields_to_return, prefix=prefix,
            delimiter='/')

        files = []
        for f in req:
            filename = os.path.basename(f.name)
            if filename != '': # Skip own folder name
                files.append(dict(
                    path=os.path.relpath(f.name, self.subdir),
                    text=filename,
                    type=f.content_type))

        directories = []
        for dir_path in req.prefixes:
            directory_name = os.path.basename(os.path.normpath(dir_path))
            directories.append(dict(
                text=directory_name,
                path=os.path.relpath(dir_path, self.subdir),
                type='group_storage',
                children=True))
            # print os.path.basename(os.path.normpath(path))

        list_dict = dict(
            name=os.path.basename(os.path.normpath(path)),
            type='group_storage',
            children = files + directories
            )

        return list_dict


    def Get(self, path):
        """Get selected file info if the path matches.

        :type path: string
        :param path: The relative path to the file.
        """
        path = os.path.join(self.subdir, path)
        f = self.bucket.blob(path)
        if f.exists():
            f.reload()
            expiration = datetime.datetime.now() + datetime.timedelta(days=1)
            expiration = int(time.mktime(expiration.timetuple()))
            file_dict = dict(
                updated=f.updated,
                name=os.path.basename(f.name),
                size=f.size,
                content_type=f.content_type,
                signed_url=f.generate_signed_url(expiration, credentials=self.credentials_p12))
            return file_dict
        else:
            return None
