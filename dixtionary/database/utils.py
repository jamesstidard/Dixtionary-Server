async def exists(entity_type, uuid, *, conn):
    return await conn.hexists(entity_type.__name__, uuid)


async def keys(entity_type, *, conn):
    return await conn.hkeys(entity_type.__name__)
