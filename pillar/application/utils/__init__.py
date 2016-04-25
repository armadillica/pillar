import copy
import json
import datetime

import bson
from eve import RFC1123_DATE_FORMAT

__all__ = ('remove_private_keys', 'PillarJSONEncoder')


def remove_private_keys(document):
    """Removes any key that starts with an underscore, returns result as new
    dictionary.
    """
    doc_copy = copy.deepcopy(document)
    for key in list(doc_copy.keys()):
        if key.startswith('_'):
            del doc_copy[key]

    return doc_copy


class PillarJSONEncoder(json.JSONEncoder):
    """JSON encoder with support for Pillar resources."""

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime(RFC1123_DATE_FORMAT)

        if isinstance(obj, bson.ObjectId):
            return str(obj)

        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)
