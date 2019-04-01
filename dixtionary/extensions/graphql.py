from graphql_ws.websockets_lib import WsLibSubscriptionServer


class GraphQL:

    def __init__(self, app, schema):

        @app.listener('before_server_start')
        async def before_server_start(app, loop):
            app.graphql = schema
            app.subscription_server = WsLibSubscriptionServer(schema)
