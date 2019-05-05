from graphql.execution.executors.asyncio import AsyncioExecutor
from graphql.execution.middleware import MiddlewareManager
from graphql_ws.websockets_lib import WsLibSubscriptionServer
from sanic_graphql import GraphQLView

from dixtionary.middleware import authorize_ws, authorize_http


class SubscriptionServer(WsLibSubscriptionServer):

    async def on_connection_init(self, connection_context, op_id, payload):
        self.connection_params = dict(payload)
        return await super().on_connection_init(connection_context, op_id, payload)


def patch_gql_ws():
    # https://github.com/graphql-python/graphql-ws/pull/10
    from graphql_ws.base import BaseSubscriptionServer
    from graphql import graphql
    assert BaseSubscriptionServer.execute

    def patched_execute(self, request_context, params):
        params.pop('context_value')
        return graphql(
            self.schema,
            **params,
            middleware=MiddlewareManager(authorize_ws, wrap_in_promise=False),
            context_value=dict(
                request=request_context,
                connection_params=self.connection_params
            ),
            allow_subscriptions=True,
        )

    BaseSubscriptionServer.execute = patched_execute


async def _websocket_handler(request, ws):
    await request.app.subscription_server.handle(ws, request)
    return ws


class GraphQL:

    def __init__(self, app, schema):
        patch_gql_ws()

        app.add_websocket_route(
            handler=_websocket_handler,
            uri='/subscriptions',
            subprotocols=['graphql-ws'],
        )

        @app.listener('before_server_start')
        async def before_server_start(app, loop):
            app.graphql = schema
            app.subscription_server = SubscriptionServer(schema, loop=loop)

            executor = AsyncioExecutor(loop=loop)
            view_kwargs = dict(
                schema=schema,
                executor=executor,
                middleware=[authorize_http],
                graphiql_version='0.10.2',
            )
            app.add_route(
                GraphQLView.as_view(**view_kwargs, graphiql=True),
                '/graphql'
            )
            app.add_route(
                GraphQLView.as_view(**view_kwargs, batch=True),
                '/graphql/batch'
            )
