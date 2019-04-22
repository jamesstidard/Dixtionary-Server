from sanic import Sanic
from sanic.response import redirect
from sanic_cors import CORS

from .model import make_schema
from .extensions import GraphQL, Redis


async def create_app(config):
    app = Sanic(__name__)
    app.config.from_object(config)

    CORS(app, automatic_options=True)
    schema = make_schema()
    GraphQL(app, schema=schema)
    Redis(app, address=app.config.REDIS_URL)

    @app.route('/')
    def handle_request(request):
        return redirect('/graphql')

    # Favicon
    # app.static('/favicon.ico', 'favicon.ico')

    return app
