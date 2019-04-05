import re


def underscore(word):
    """
    Make an underscored, lowercase form from the expression in the string.

    >>> underscore("DeviceType")
    "device_type"
    """
    word = re.sub(r"([A-Z]+)([A-Z][a-z])", r'\1_\2', word)
    word = re.sub(r"([a-z\d])([A-Z])", r'\1_\2', word)
    word = word.replace("-", "_")
    return word.lower()
