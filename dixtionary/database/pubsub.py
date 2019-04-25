import aioredis

from dixtionary.utils import json


async def broadcaster(**kwargs):
    redis = await aioredis.create_redis(**kwargs)
    channel, *_ = await redis.subscribe("BROADCASTS")

    try:
        while await channel.wait_message():
            data = await channel.get()
            message = json.loads(data)
            yield message['name'], message['data']
    finally:
        redis.close()
        await redis.wait_closed()


async def subscribe(channel, broadcaster):
    normal = channel.upper()
    async for name, data in broadcaster:
        if name == normal:
            yield data


async def publish(channel, data, *, conn):
    message = dict(name=channel.upper(), data=data)
    await conn.publish("BROADCASTS", json.dumps(message))
