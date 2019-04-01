from json import loads as json_loads

from sanic.request import Request
from sanic.response import json

from graphql.execution.executors.asyncio import AsyncioExecutor

from dixtionary.middleware import authorize
from dixtionary.model import Context


async def graphql_handler(request: Request):
    if request.method == 'GET':
        payload = request.raw_args
    elif request.method == 'POST':
        payload = request.json
    else:
        message = f"{request.method} not implemented"
        raise NotImplementedError(message)

    result = await request.app.graphql.execute(
        request_string=payload.get('query'),
        operation_name=payload.get('operationName'),
        variables=payload.get('variables'),
        context=Context(request=request),
        middleware=[authorize],
        executor=AsyncioExecutor(loop=request.app.loop),
        return_promise=True,
    )

    return json(result, indent=2)
