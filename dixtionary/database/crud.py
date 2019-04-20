from dixtionary.utils import json
from .pubsub import publish


async def select(entity_type, uuid, *, conn):
    data = await conn.hget(entity_type.__name__, uuid)

    if data is None:
        raise IndexError(f"No record found for {entity_type} {uuid}")

    return entity_type(**json.loads(data))


async def insert(entity, *, conn):
    type_ = type(entity).__name__
    key = entity.uuid
    data = json.dumps(entity)
    await conn.hset(type_, key, data)
    await publish(f"{type_}_INSERTED", data, conn=conn)


async def update(entity, *, conn):
    type_ = type(entity).__name__
    key = entity.uuid
    data = json.dumps(entity)
    await conn.hset(type_, key, data)
    await publish(f"{type_}_UPDATED", data, conn=conn)


async def delete(entity, *, conn):
    type_ = type(entity).__name__
    key = entity.uuid
    data = json.dumps(entity)
    await conn.hdel(type_, key)
    await publish(f"{type_}_DELETED", data, conn=conn)
