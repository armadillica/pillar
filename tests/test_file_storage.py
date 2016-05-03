import os
import tempfile

from common_test_class import AbstractPillarTest


class TempDirTest(AbstractPillarTest):
    def test_tempfiles_location(self):
        # After importing the application, tempfiles should be created in the STORAGE_DIR
        storage = self.app.config['STORAGE_DIR']
        self.assertEqual(os.environ['TMP'], storage)
        self.assertNotIn('TEMP', os.environ)
        self.assertNotIn('TMPDIR', os.environ)

        handle, filename = tempfile.mkstemp()
        os.close(handle)
        dirname = os.path.dirname(filename)
        self.assertEqual(dirname, storage)

        tmpfile = tempfile.NamedTemporaryFile()
        dirname = os.path.dirname(tmpfile.name)
        self.assertEqual(dirname, storage)

