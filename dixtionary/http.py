from sanic.request import Request
from sanic.response import json


async def http_handler(request: Request):
    query = request.raw_args.get('query')
    result = request.app.schema.execute(query, context=request)
    return json(result.data, indent=2)
