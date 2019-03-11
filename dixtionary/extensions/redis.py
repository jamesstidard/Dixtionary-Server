import aioredis


class Redis:

    def __init__(self, app, **kwargs):
        @app.listener('before_server_start')
        async def before_server_start(app, loop):
            app.redis = await aioredis.create_redis_pool(**kwargs, loop=loop)

        @app.listener('after_server_stop')
        async def after_server_stop(app, loop):
            await app.redis.wait_closed()
