from sanic import Sanic

from .websocket import websocket_handler


async def create_app(config):
    app = Sanic(__name__)
    app.config.from_object(config)

    # Favicon
    # app.static('/favicon.ico', 'favicon.ico')

    # API
    # app.add_route(http_handler, '/api/<action>')
    app.add_websocket_route(websocket_handler, '/api')

    return app
