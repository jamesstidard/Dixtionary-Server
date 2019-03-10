from sanic.request import Request as Request
from sanic.response import json

from .model import schema


async def http_handler(request: Request):
    query = request.raw_args.get('q')
    result = schema.execute(query)
    return json(result.data)

import os
print(os.environ)
