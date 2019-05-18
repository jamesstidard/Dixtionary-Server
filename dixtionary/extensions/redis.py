from functools import partial

import aioredis

from dixtionary.database.pubsub import subscribe, broadcaster
from dixtionary.utils.asynchronous import hotstream


class Redis:
    def __init__(self, app, **kwargs):
        @app.listener("before_server_start")
        async def before_server_start(app, loop):
            app.redis = await aioredis.create_redis_pool(**kwargs, loop=loop)
            app.broadcaster = await hotstream(broadcaster(**kwargs)).stream()
            app.subscribe = partial(subscribe, broadcaster=app.broadcaster)
            await app.redis.flushall()

        @app.listener("after_server_stop")
        async def after_server_stop(app, loop):
            await app.broadcaster.aclose()
            app.redis.close()
            await app.redis.wait_closed()
