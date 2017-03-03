# -*- encoding: utf-8 -*-

import unittest
import datetime

from bson import tz_util
from pillar.web import utils


class IsValidIdTest(unittest.TestCase):
    def test_valid(self):
        # 24-byte hex strings
        self.assertTrue(utils.is_valid_id(24 * 'a'))
        self.assertTrue(utils.is_valid_id(24 * 'a'))
        self.assertTrue(utils.is_valid_id('deadbeefbeefcacedeadcace'))
        self.assertTrue(utils.is_valid_id('deadbeefbeefcacedeadcace'))

        # 12-byte arbitrary ASCII bytes
        self.assertTrue(utils.is_valid_id(b'DeadBeefCake'))
        self.assertTrue(utils.is_valid_id(b'DeadBeefCake'))

        # 12-byte object
        self.assertTrue(utils.is_valid_id('beef€67890'.encode()))

    def test_bad_length(self):
        self.assertFalse(utils.is_valid_id(23 * 'a'))
        self.assertFalse(utils.is_valid_id(25 * 'a'))

    def test_non_string(self):
        self.assertFalse(utils.is_valid_id(None))
        self.assertFalse(utils.is_valid_id(1234))
        self.assertFalse(utils.is_valid_id([24 * 'a']))

    def test_bad_content(self):
        # 24-character non-hexadecimal string
        self.assertFalse(utils.is_valid_id('deadbeefbeefcakedeadcake'))

        # unicode variant of valid 12-byte str object
        self.assertFalse(utils.is_valid_id('beef€67890'))


class PrettyDateTest(unittest.TestCase):
    def test_none(self):
        from pillar.web.utils import pretty_date

        self.assertIsNone(pretty_date(None))

    def test_past(self):
        from pillar.web.utils import pretty_date

        now = datetime.datetime(2016, 11, 8, 11, 46, 30, 0, tz_util.utc)  # a Tuesday

        def pd(**diff):
            return pretty_date(now - datetime.timedelta(**diff), now=now)

        self.assertEqual('just now', pd(seconds=5))
        self.assertEqual('5m ago', pd(minutes=5))
        self.assertEqual('last Tuesday', pd(days=7))
        self.assertEqual('1 week ago', pd(days=8))
        self.assertEqual('2 weeks ago', pd(days=14))
        self.assertEqual('08 Oct', pd(days=31))
        self.assertEqual('08 Oct 2015', pd(days=31 + 366))

    def test_future(self):
        from pillar.web.utils import pretty_date

        def pd(**diff):
            return pretty_date(now + datetime.timedelta(**diff), now=now)

        now = datetime.datetime(2016, 11, 8, 11, 46, 30, 0, tz_util.utc)  # a Tuesday
        self.assertEqual('just now', pd(seconds=5))
        self.assertEqual('in 5m', pd(minutes=5))
        self.assertEqual('next Tuesday', pd(days=7))
        self.assertEqual('in 1 week', pd(days=8))
        self.assertEqual('in 2 weeks', pd(days=14))
        self.assertEqual('08 Dec', pd(days=30))
        self.assertEqual('08 Dec 2017', pd(days=30 + 365))

    def test_past_with_time(self):
        from pillar.web.utils import pretty_date

        now = datetime.datetime(2016, 11, 8, 11, 46, 30, 0, tz_util.utc)  # a Tuesday

        def pd(**diff):
            return pretty_date(now - datetime.timedelta(**diff), detail=True, now=now)

        self.assertEqual('just now', pd(seconds=5))
        self.assertEqual('5m ago', pd(minutes=5))
        self.assertEqual('last Tuesday at 11:46', pd(days=7))
        self.assertEqual('1 week ago at 11:46', pd(days=8))
        self.assertEqual('2 weeks ago at 11:46', pd(days=14))
        self.assertEqual('08 Oct at 11:46', pd(days=31))
        self.assertEqual('08 Oct 2015 at 11:46', pd(days=31 + 366))

    def test_future_with_time(self):
        from pillar.web.utils import pretty_date

        def pd(**diff):
            return pretty_date(now + datetime.timedelta(**diff), detail=True, now=now)

        now = datetime.datetime(2016, 11, 8, 11, 46, 30, 0, tz_util.utc)  # a Tuesday
        self.assertEqual('just now', pd(seconds=5))
        self.assertEqual('in 5m', pd(minutes=5))
        self.assertEqual('next Tuesday at 11:46', pd(days=7))
        self.assertEqual('in 1 week at 11:46', pd(days=8))
        self.assertEqual('in 2 weeks at 11:46', pd(days=14))
        self.assertEqual('08 Dec at 11:46', pd(days=30))
        self.assertEqual('08 Dec 2017 at 11:46', pd(days=30 + 365))


class EvePaginationTest(unittest.TestCase):
    def test_last_page_index(self):
        from pillar.web.utils import last_page_index as lpi

        self.assertEqual(1, lpi({'total': 0, 'max_results': 313}))
        self.assertEqual(1, lpi({'total': 5, 'max_results': 10}))
        self.assertEqual(1, lpi({'total': 5, 'max_results': 5}))
        self.assertEqual(2, lpi({'total': 6, 'max_results': 5}))
        self.assertEqual(2, lpi({'total': 9, 'max_results': 5}))
        self.assertEqual(2, lpi({'total': 10, 'max_results': 5}))
        self.assertEqual(3, lpi({'total': 11, 'max_results': 5}))
        self.assertEqual(404129352, lpi({'total': 2828905463, 'max_results': 7}))
