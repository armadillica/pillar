import copy
import json
import datetime

import bson
from eve import RFC1123_DATE_FORMAT


def remove_private_keys(document):
    """Removes any key that starts with an underscore, returns result as new
    dictionary.
    """
    patch_info = copy.deepcopy(document)
    for key in list(patch_info.keys()):
        if key.startswith('_'):
            del patch_info[key]

    return patch_info


class PillarJSONEncoder(json.JSONEncoder):
    """JSON encoder with support for Pillar resources."""

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            if obj.tzinfo is None:
                raise ValueError('All datetime.datetime objects should be timezone-aware.')
            return obj.strftime(RFC1123_DATE_FORMAT)

        if isinstance(obj, bson.ObjectId):
            return str(obj)

        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)
