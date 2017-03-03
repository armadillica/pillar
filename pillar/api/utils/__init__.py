import copy
import hashlib
import json
import urllib.request, urllib.parse, urllib.error

import datetime
import functools
import logging

import bson.objectid
from eve import RFC1123_DATE_FORMAT
from flask import current_app
from werkzeug import exceptions as wz_exceptions
import pymongo.results

log = logging.getLogger(__name__)


def node_setattr(node, key, value):
    """Sets a node property by dotted key.

    Modifies the node in-place. Deletes None values.

    :type node: dict
    :type key: str
    :param value: the value to set, or None to delete the key.
    """

    set_on = node
    while key and '.' in key:
        head, key = key.split('.', 1)
        set_on = set_on[head]

    if value is None:
        set_on.pop(key, None)
    else:
        set_on[key] = value


def remove_private_keys(document):
    """Removes any key that starts with an underscore, returns result as new
    dictionary.
    """
    doc_copy = copy.deepcopy(document)
    for key in list(doc_copy.keys()):
        if key.startswith('_'):
            del doc_copy[key]

    try:
        del doc_copy['allowed_methods']
    except KeyError:
        pass

    return doc_copy


class PillarJSONEncoder(json.JSONEncoder):
    """JSON encoder with support for Pillar resources."""

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime(RFC1123_DATE_FORMAT)

        if isinstance(obj, bson.ObjectId):
            return str(obj)

        if isinstance(obj, pymongo.results.UpdateResult):
            return obj.raw_result

        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


def dumps(mongo_doc, **kwargs):
    """json.dumps() for MongoDB documents."""
    return json.dumps(mongo_doc, cls=PillarJSONEncoder, **kwargs)


def jsonify(mongo_doc, status=200, headers=None):
    """JSonifies a Mongo document into a Flask response object."""
    
    return current_app.response_class(dumps(mongo_doc),
                                      mimetype='application/json',
                                      status=status,
                                      headers=headers)


def bsonify(mongo_doc, status=200, headers=None):
    """BSonifies a Mongo document into a Flask response object."""

    import bson

    data = bson.BSON.encode(mongo_doc)
    return current_app.response_class(data,
                                      mimetype='application/bson',
                                      status=status,
                                      headers=headers)


def skip_when_testing(func):
    """Decorator, skips the decorated function when app.config['TESTING']"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if current_app.config['TESTING']:
            log.debug('Skipping call to %s(...) due to TESTING', func.__name__)
            return None

        return func(*args, **kwargs)
    return wrapper


def project_get_node_type(project_document, node_type_node_name):
    """Return a node_type subdocument for a project. If none is found, return
    None.
    """

    if project_document is None:
        return None

    return next((node_type for node_type in project_document['node_types']
                 if node_type['name'] == node_type_node_name), None)


def str2id(document_id):
    """Returns the document ID as ObjectID, or raises a BadRequest exception.

    :type document_id: str
    :rtype: bson.ObjectId
    :raises: wz_exceptions.BadRequest
    """

    if not document_id:
        log.debug('str2id(%r): Invalid Object ID', document_id)
        raise wz_exceptions.BadRequest('Invalid object ID %r' % document_id)

    try:
        return bson.ObjectId(document_id)
    except (bson.objectid.InvalidId, TypeError):
        log.debug('str2id(%r): Invalid Object ID', document_id)
        raise wz_exceptions.BadRequest('Invalid object ID %r' % document_id)


def gravatar(email: str, size=64):
    parameters = {'s': str(size), 'd': 'mm'}
    return "https://www.gravatar.com/avatar/" + \
           hashlib.md5(email.encode()).hexdigest() + \
           "?" + urllib.parse.urlencode(parameters)


class MetaFalsey(type):
    def __bool__(cls):
        return False


class DoesNotExist(object, metaclass=MetaFalsey):
    """Returned as value by doc_diff if a value does not exist."""


def doc_diff(doc1, doc2, falsey_is_equal=True):
    """Generator, yields differences between documents.

    Yields changes as (key, value in doc1, value in doc2) tuples, where
    the value can also be the DoesNotExist class. Does not report changed
    private keys (i.e. starting with underscores).

    Sub-documents (i.e. dicts) are recursed, and dot notation is used
    for the keys if changes are found.

    If falsey_is_equal=True, all Falsey values compare as equal, i.e. this
    function won't report differences between DoesNotExist, False, '', and 0.
    """

    for key in set(doc1.keys()).union(set(doc2.keys())):
        if isinstance(key, str) and key[0] == '_':
            continue

        val1 = doc1.get(key, DoesNotExist)
        val2 = doc2.get(key, DoesNotExist)

        # Only recurse if both values are dicts
        if isinstance(val1, dict) and isinstance(val2, dict):
            for subkey, subval1, subval2 in doc_diff(val1, val2):
                yield '%s.%s' % (key, subkey), subval1, subval2
            continue

        if val1 == val2:
            continue
        if falsey_is_equal and bool(val1) == bool(val2) == False:
            continue

        yield key, val1, val2
