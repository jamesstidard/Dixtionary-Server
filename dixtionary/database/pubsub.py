from contextlib import asynccontextmanager

import aioredis

from dixtionary.utils import json


async def messages(channel):
    while await channel.wait_message():
        data = await channel.get()
        yield json.loads(data)


@asynccontextmanager
async def subscribe(channel, **kwargs):
    redis = await aioredis.create_redis(**kwargs)
    channel, = await redis.subscribe(channel.upper())
    try:
        yield messages(channel)
    finally:
        redis.close()
        await redis.wait_closed()


async def publish(channel, data, *, conn):
    await conn.publish(channel.upper(), data)
