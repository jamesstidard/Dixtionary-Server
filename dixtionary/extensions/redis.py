from collections import namedtuple
from contextlib import asynccontextmanager
from functools import partial

import aioredis

from dixtionary.utils.redis import loads, dumps

RedisConfig = namedtuple('RedisConfig', 'pool publish subscribe')


async def messages(channel):
    while await channel.wait_message():
        data = await channel.get()
        yield loads(data)


@asynccontextmanager
async def subscribe(channel, **kwargs):
    redis = await aioredis.create_redis(**kwargs)
    channel, = await redis.subscribe(channel.upper())
    try:
        yield messages(channel)
    finally:
        redis.close()
        await redis.wait_closed()


async def publish(channel, message, *, pool):
    *_, data = dumps(message)
    await pool.publish(channel.upper(), data)


class Redis:

    def __init__(self, app, **kwargs):
        @app.listener('before_server_start')
        async def before_server_start(app, loop):
            pool = await aioredis.create_redis_pool(**kwargs, loop=loop)
            app.redis = RedisConfig(
                pool=pool,
                publish=partial(publish, pool=pool),
                subscribe=partial(subscribe, **kwargs, loop=loop),
            )

        @app.listener('after_server_stop')
        async def after_server_stop(app, loop):
            app.redis.pool.close()
            await app.redis.pool.wait_closed()
