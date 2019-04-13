import json

from datetime import datetime

import graphene


def _default(obj):
    if isinstance(obj, graphene.ObjectType):
        return obj.uuid
    elif isinstance(obj, datetime):
        return dict(__type__='timestamp', value=obj.timestamp())
    raise ValueError(f'Unable to serialize {type(obj)}')


def dumps(entity: graphene.ObjectType):
    type_ = str(type(entity))
    key = entity.uuid
    value = json.dumps(vars(entity), default=_default)
    return type_, key, value


def _hook(obj):
    if obj.get('__type__') == 'timestamp':
        return datetime.fromtimestamp(obj['value'])
    else:
        return obj


def loads(value, *, entity=None):
    if isinstance(value, bytes):
        value = value.decode('utf-8')
    data = json.loads(value, object_hook=_hook)
    if entity:
        return entity(**data)
    else:
        return data
