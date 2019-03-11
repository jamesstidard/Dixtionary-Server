
class GraphQL:

    def __init__(self, app, schema):
        @app.listener('before_server_start')
        async def before_server_start(app, loop):
            app.graphql = schema
