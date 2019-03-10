import graphene

from sanic import Sanic
from sanic.response import json

from .model import Query
from .http import http_handler
from .websocket import websocket_handler


async def create_app(config):
    app = Sanic(__name__)
    app.config.from_object(config)

    @app.listener('before_server_start')
    async def before_server_start(app, loop):
        app.schema = graphene.Schema(Query)

    # Favicon
    # app.static('/favicon.ico', 'favicon.ico')

    # API
    app.add_route(http_handler, '/http')
    # app.add_websocket_route(websocket_handler, '/ws')

    return app
