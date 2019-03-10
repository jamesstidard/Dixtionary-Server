from sanic import Sanic
from sanic.response import json

from .model import make_schema
from .handlers.http import graphql_handler
from .handlers.websocket import websocket_handler


async def create_app(config):
    app = Sanic(__name__)
    app.config.from_object(config)

    @app.listener('before_server_start')
    async def before_server_start(app, loop):
        app.state = {}
        app.schema = make_schema()

    # Favicon
    # app.static('/favicon.ico', 'favicon.ico')

    # API
    app.add_route(graphql_handler, '/graphql')
    # app.add_websocket_route(websocket_handler, '/ws')

    return app
