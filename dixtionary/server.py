from edgedb import async_connect

from sanic import Sanic
from sanic.response import json

from .websocket import websocket_handler
from .http import http_handler


async def create_app(config):
    app = Sanic(__name__)
    app.config.from_object(config)

    @app.listener('before_server_start')
    async def before_server_start(app, loop):
        app.db = await async_connect(
            dsn='edgedb://dixtionary@0.0.0.0:5656/dixtionary',
        )

    @app.listener('after_server_stop')
    async def after_server_stop(app, loop):
        await app.db.close()

    # Favicon
    # app.static('/favicon.ico', 'favicon.ico')

    @app.get('/test')
    async def test(request):
        print("testing")
        await request.app.db.execute('''
            CREATE TABLE users(
                id serial PRIMARY KEY,
                name text,
                dob date
            )
        ''')
        return json(True)

    # API
    app.add_route(http_handler, '/http')
    # app.add_websocket_route(websocket_handler, '/ws')

    return app
