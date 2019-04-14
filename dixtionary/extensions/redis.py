from functools import partial

import aioredis

from dixtionary.database.pubsub import subscribe


class Redis:

    def __init__(self, app, **kwargs):

        @app.listener('before_server_start')
        async def before_server_start(app, loop):
            app.redis = await aioredis.create_redis_pool(**kwargs, loop=loop)
            app.subscribe = partial(subscribe, **kwargs, loop=loop)

        @app.listener('after_server_stop')
        async def after_server_stop(app, loop):
            app.redis.close()
            await app.redis.wait_closed()
