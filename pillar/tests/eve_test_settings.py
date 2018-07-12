from pillar.api.eve_settings import *

MONGO_DBNAME = 'pillar_test'
MONGO_USERNAME = None


def override_eve():
    from eve.tests import test_settings
    from eve import tests

    test_settings.MONGO_HOST = MONGO_HOST
    test_settings.MONGO_PORT = MONGO_PORT
    test_settings.MONGO_DBNAME = MONGO_DBNAME
    test_settings.MONGO1_USERNAME = MONGO_USERNAME
    tests.MONGO_HOST = MONGO_HOST
    tests.MONGO_DBNAME = MONGO_DBNAME
    tests.MONGO_USERNAME = MONGO_USERNAME
