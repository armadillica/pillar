"""Extra functionality for attrs."""

import functools
import logging

import attr

string = functools.partial(attr.ib, validator=attr.validators.instance_of(str))


def log(name):
    """Returns a logger attr.ib

    :param name: name to pass to logging.getLogger()
    :rtype: attr.ib
    """
    return attr.ib(default=logging.getLogger(name),
                   repr=False,
                   hash=False,
                   cmp=False)
