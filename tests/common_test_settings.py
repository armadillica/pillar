from settings import *

from eve.tests.test_settings import MONGO_DBNAME


def override_eve():
    from eve.tests import test_settings
    from eve import tests

    test_settings.MONGO_HOST = MONGO_HOST
    test_settings.MONGO_PORT = MONGO_PORT
    tests.MONGO_HOST = MONGO_HOST
    tests.MONGO_PORT = MONGO_PORT
