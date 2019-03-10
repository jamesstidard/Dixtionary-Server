from sanic.request import Request
from sanic.response import json

from graphene import Schema


async def graphql_handler(request: Request):
    query: str = request.raw_args.get('query')
    schema: Schema = request.app.schema

    result = schema.execute(query, context=request)

    if result.errors:
        raise ValueError(result.errors)
    else:
        return json(result.data, indent=2)
