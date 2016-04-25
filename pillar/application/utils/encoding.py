import os

from flask import current_app
from zencoder import Zencoder

from application import encoding_service_client


class Encoder:
    """Generic Encoder wrapper. Provides a consistent API, independent from
    the encoding backend enabled.
    """

    @staticmethod
    def job_create(src_file):
        """Create an encoding job. Return the backend used as well as an id.
        """
        if isinstance(encoding_service_client, Zencoder):
            if src_file['backend'] == 'gcs':
                # Build the specific GCS input url, assuming the file is stored
                # in the _ subdirectory
                storage_base = "gcs://{0}/_/".format(src_file['project'])
            file_input = os.path.join(storage_base, src_file['file_path'])
            outputs = []
            options = dict(notifications=current_app.config['ZENCODER_NOTIFICATIONS_URL'])
            for v in src_file['variations']:
                outputs.append({
                    'format': v['format'],
                    'witdh': v['width'],
                    'url': os.path.join(storage_base, v['file_path'])})
            r = encoding_service_client.job.create(file_input, outputs=outputs,
                                                   options=options)
            if r.code == 201:
                return dict(process_id=r.body['id'], backend='zencoder')
            else:
                return None
        else:
            return None

    @staticmethod
    def job_progress(job_id):
        if isinstance(encoding_service_client, Zencoder):
            r = encoding_service_client.job.progress(int(job_id))
            return r.body
        else:
            return None
