from sanic.request import Request
from sanic.response import json

from dixtionary.middleware import authorize


async def graphql_handler(request: Request):
    if request.method == 'GET':
        payload = request.raw_args
    elif request.method == 'POST':
        payload = request.json
    else:
        message = f"{request.method} not implemented"
        raise NotImplementedError(message)

    result = request.app.schema.execute(
        request_string=payload.get('query'),
        operation_name=payload.get('operationName'),
        variables=payload.get('variables'),
        context=request,
        middleware=[authorize]
    )

    return json(result, indent=2)
