from collections import namedtuple
from contextlib import asynccontextmanager
from functools import partial

import aioredis

RedisConfig = namedtuple('RedisConfig', 'subscribe pool')


async def messages(channel):
    while await channel.wait_message():
        yield await channel.get_json()


@asynccontextmanager
async def subscribe(channel, **kwargs):
    redis = await aioredis.create_redis(**kwargs)
    channel, = await redis.subscribe(channel)
    try:
        yield messages(channel)
    finally:
        redis.close()
        await redis.wait_closed()


class Redis:

    def __init__(self, app, **kwargs):
        @app.listener('before_server_start')
        async def before_server_start(app, loop):
            app.redis = RedisConfig(
                subscribe=partial(subscribe, **kwargs, loop=loop),
                pool=await aioredis.create_redis_pool(**kwargs, loop=loop),
            )

        @app.listener('after_server_stop')
        async def after_server_stop(app, loop):
            app.redis.pool.close()
            await app.redis.pool.wait_closed()
