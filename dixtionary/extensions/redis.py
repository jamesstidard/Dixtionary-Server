import asyncio
from functools import partial

import aioredis
from aiostream.stream import iterate, count

from dixtionary.database.pubsub import subscribe, broadcaster
from dixtionary.utils.asynchronous import hotstream


class Redis:

    def __init__(self, app, **kwargs):

        @app.listener('before_server_start')
        async def before_server_start(app, loop):
            app.redis = await aioredis.create_redis_pool(**kwargs, loop=loop)
            app.broadcaster = await hotstream(broadcaster(**kwargs)).stream().__aenter__()
            app.subscribe = partial(subscribe, broadcaster=app.broadcaster)
            await app.redis.flushall()

        @app.listener('after_server_stop')
        async def after_server_stop(app, loop):
            await app.broadcaster.__aexit__()
            app.redis.close()
            await app.redis.wait_closed()
