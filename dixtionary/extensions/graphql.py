from graphql.execution.executors.asyncio import AsyncioExecutor
from graphql_ws.websockets_lib import WsLibSubscriptionServer
from sanic_graphql import GraphQLView

from dixtionary.middleware import authorize


async def _websocket_handler(request, ws):
    await request.app.subscription_server.handle(ws)
    return ws


class GraphQL:

    def __init__(self, app, schema):

        @app.listener('before_server_start')
        async def before_server_start(app, loop):
            app.graphql = schema
            app.subscription_server = WsLibSubscriptionServer(schema)

            executor = AsyncioExecutor(loop=loop)
            view_kwargs = dict(
                schema=schema,
                executor=executor,
                middleware=[authorize],
            )
            app.add_route(
                GraphQLView.as_view(**view_kwargs, graphiql=True),
                '/graphql'
            )
            app.add_route(
                GraphQLView.as_view(**view_kwargs, batch=True),
                '/graphql/batch'
            )
            app.add_websocket_route(
                handler=_websocket_handler,
                uri='/subscriptions',
                subprotocols=['graphql-ws'],
            )
