import json

import graphene


def _default(obj):
    if isinstance(obj, graphene.ObjectType):
        return obj.uuid
    raise ValueError(f'Unable to serialize {type(obj)}')


def dumps(entity: graphene.ObjectType):
    type_ = str(type(entity))
    key = entity.uuid
    value = json.dumps(vars(entity), default=_default)
    return type_, key, value


def loads(value):
    return json.loads(value.decode('utf-8'))
