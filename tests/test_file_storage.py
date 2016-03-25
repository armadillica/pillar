"""Test cases for file handling."""

from __future__ import print_function

import os
import shutil
import copy
import json

from common_test_class import AbstractPillarTest, MY_PATH
from common_test_data import EXAMPLE_FILE


class FileUploadingTest(AbstractPillarTest):
    def test_create_file_missing_on_fs(self):
        from application.utils import PillarJSONEncoder, remove_private_keys

        to_post = remove_private_keys(EXAMPLE_FILE)
        json_file = json.dumps(to_post, cls=PillarJSONEncoder)

        with self.app.test_request_context():
            self.ensure_project_exists()

            resp = self.client.post('/files',
                                    data=json_file,
                                    headers={'Content-Type': 'application/json'})

        self.assertEqual(422, resp.status_code)

    def test_create_file_exists_on_fs(self):
        from application.utils import PillarJSONEncoder, remove_private_keys

        filename = 'BlenderDesktopLogo.png'
        full_file = copy.deepcopy(EXAMPLE_FILE)
        full_file[u'name'] = filename
        to_post = remove_private_keys(full_file)
        json_file = json.dumps(to_post, cls=PillarJSONEncoder)

        with self.app.test_request_context():
            self.ensure_project_exists()

            target_dir = os.path.join(self.app.config['SHARED_DIR'], filename[:2])
            if os.path.exists(target_dir):
                assert os.path.isdir(target_dir)
            else:
                os.makedirs(target_dir)
            shutil.copy(os.path.join(MY_PATH, filename), target_dir)

            resp = self.client.post('/files',
                                    data=json_file,
                                    headers={'Content-Type': 'application/json'})

        self.assertEqual(201, resp.status_code)
