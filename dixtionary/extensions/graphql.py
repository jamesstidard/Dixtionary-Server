from graphql.execution.executors.asyncio import AsyncioExecutor
from graphql_ws.websockets_lib import WsLibSubscriptionServer
from sanic_graphql import GraphQLView

from dixtionary.middleware import authorize


def patch_gql_ws():
    # https://github.com/graphql-python/graphql-ws/pull/10
    from graphql_ws.base import BaseSubscriptionServer
    from graphql import graphql
    assert BaseSubscriptionServer.execute

    def patched_execute(self, request_context, params):
        try:
            return graphql(
                self.schema,
                #**dict(params, allow_subscriptions=True))
                **dict(params, context_value=dict(request=request_context), allow_subscriptions=True))
        except BaseException as e:
            raise e

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
            app.subscription_server = WsLibSubscriptionServer(schema)

            executor = AsyncioExecutor(loop=loop)
            view_kwargs = dict(
                schema=schema,
                executor=executor,
                middleware=[authorize],
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
