import aioredis

from sanic import Sanic

from sanic_cors import CORS

from .model import make_schema
from .extensions import GraphQL, Redis
from .handlers.http import graphql_handler
# from .handlers.websocket import websocket_handler


async def create_app(config):
    app = Sanic(__name__)
    app.config.from_object(config)

    CORS(app, automatic_options=True)
    GraphQL(app, schema=make_schema())
    Redis(app, address=app.config.DATABASE_URL)

    # Favicon
    # app.static('/favicon.ico', 'favicon.ico')

    # API
    app.add_route(graphql_handler, '/graphql', methods=['GET', 'POST'])
    # app.add_websocket_route(websocket_handler, '/ws')

    return app
