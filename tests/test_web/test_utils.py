# -*- encoding: utf-8 -*-

import unittest

from pillar.web import utils


class IsValidIdTest(unittest.TestCase):
    def test_valid(self):
        # 24-byte hex strings
        self.assertTrue(utils.is_valid_id(24 * 'a'))
        self.assertTrue(utils.is_valid_id(24 * u'a'))
        self.assertTrue(utils.is_valid_id('deadbeefbeefcacedeadcace'))
        self.assertTrue(utils.is_valid_id(u'deadbeefbeefcacedeadcace'))

        # 12-byte arbitrary ASCII strings
        self.assertTrue(utils.is_valid_id('DeadBeefCake'))
        self.assertTrue(utils.is_valid_id(u'DeadBeefCake'))

        # 12-byte str object
        self.assertTrue(utils.is_valid_id('beef€67890'))

    def test_bad_length(self):
        self.assertFalse(utils.is_valid_id(23 * 'a'))
        self.assertFalse(utils.is_valid_id(25 * u'a'))

    def test_non_string(self):
        self.assertFalse(utils.is_valid_id(None))
        self.assertFalse(utils.is_valid_id(1234))
        self.assertFalse(utils.is_valid_id([24 * 'a']))

    def test_bad_content(self):
        # 24-character non-hexadecimal string
        self.assertFalse(utils.is_valid_id('deadbeefbeefcakedeadcake'))

        # unicode variant of valid 12-byte str object
        self.assertFalse(utils.is_valid_id(u'beef€67890'))
