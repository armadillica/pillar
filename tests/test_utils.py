# -*- encoding: utf-8 -*-

from bson import ObjectId
from werkzeug.exceptions import BadRequest

from common_test_class import AbstractPillarTest


class Str2idTest(AbstractPillarTest):
    def test_happy(self):
        from application.utils import str2id

        def happy(str_id):
            self.assertEqual(ObjectId(str_id), str2id(str_id))

        happy(24 * 'a')
        happy(12 * 'a')
        happy(u'577e23ad98377323f74c368c')

    def test_unhappy(self):
        from application.utils import str2id

        def unhappy(str_id):
            self.assertRaises(BadRequest, str2id, str_id)

        unhappy(13 * 'a')
        unhappy(u'577e23ad 8377323f74c368c')
        unhappy(u'김치')  # Kimchi
        unhappy('')
        unhappy(u'')
        unhappy(None)
