"""Extra functionality for attrs."""

import functools
import logging

import attr

string = functools.partial(attr.ib, validator=attr.validators.instance_of(str))


def log(name):
    """Returns a logger

    :param name: name to pass to logging.getLogger()
    """
    return logging.getLogger(name)
