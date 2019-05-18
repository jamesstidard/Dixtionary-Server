import json as _json

from datetime import datetime

import graphene


def _default(obj):
    if isinstance(obj, graphene.ObjectType):
        return obj.uuid
    elif isinstance(obj, datetime):
        return dict(__type__="timestamp", value=obj.timestamp())
    else:
        raise ValueError(f"Unable to serialize {type(obj)}")


def dumps(entity: graphene.ObjectType):
    return _json.dumps(entity, default=_default)


def _hook(obj):
    if obj.get("__type__") == "timestamp":
        return datetime.fromtimestamp(obj["value"])
    else:
        return obj


def loads(value):
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    return _json.loads(value, object_hook=_hook)
