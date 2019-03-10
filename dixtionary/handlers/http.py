from sanic.request import Request
from sanic.response import json

from graphene import Schema

from dixtionary.model.context import Context
from .utils import authentication as auth


async def graphql_handler(request: Request):
    user = auth.get_current_user(request=request)

    query: str = request.raw_args.get('query')
    schema: Schema = request.app.schema

    context = Context(
        state=request.app.state,
        current_user=user,
    )

    result = schema.execute(query, context=context)

    if result.errors:
        raise ValueError(result.errors)
    else:
        response = json(result.data, indent=2)

        # context.current_user can be mutated in schema.execute
        auth.set_current_user(
            user=context.current_user,
            request=request,
            response=response
        )

        return response
