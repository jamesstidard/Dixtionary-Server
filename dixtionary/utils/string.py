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


def str_list(items, oxford_comma=True, conjunctive='&', quoted=True):
    items = list(items)

    if quoted:
        items = [f'"{i}"' for i in items]

    if len(items) <= 1:
        return ''.join(items)
    else:
        *head, tail = items

        if oxford_comma:
            tail = f', {conjunctive} {tail}'
        else:
            tail = f' {conjunctive} {tail}'

        return ', '.join(head) + tail
