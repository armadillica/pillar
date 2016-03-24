import copy


def remove_private_keys(document):
    """Removes any key that starts with an underscore, returns result as new
    dictionary.
    """
    patch_info = copy.deepcopy(document)
    for key in list(patch_info.keys()):
        if key.startswith('_'):
            del patch_info[key]

    return patch_info
