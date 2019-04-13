from promise import Promise
from itsdangerous import Serializer, BadSignature

from dixtionary.model.query import User
from dixtionary.utils import redis


# https://github.com/graphql-python/graphql-core/issues/149
# def next_subscription(next):
#     async def next_(root, info, **args):
#         async def inner():
#             result = next(root, info, **args)
#             if isinstance(result, Promise):
#                 result = result.get()
#             async for msg in result:
#                 yield msg
#         return inner()
#     return next_


async def authorize(next, root, info, **args):
    is_query = info.operation.operation == 'query'
    is_subscription = info.operation.operation == 'subscription'
    read_only = (
        (is_query or is_subscription)
        # and not info.field_name == 'joinRoom' NOTE: Auth via token as https://github.com/Akryum/vue-apollo/issues/520
    )
    login = 'login' == info.path[0]

    # if is_subscription:
    #     next = next_subscription(next)

    try:
        token = info.context["request"].headers["authorization"]
    except KeyError:
        if read_only or login:
            return await next(root, info, **args)
        else:
            msg = "token variable required for access. Try the login endpoint."
            raise ValueError(msg)
    else:
        token = token.replace('Bearer ', '')

    serializer = Serializer(info.context["request"].app.config.SECRET)

    try:
        user = serializer.loads(token)
    except BadSignature:
        msg = "Looks like you've been tampering with you token. Get out."
        raise ValueError(msg)

    # maybe server database has been cleared.
    # insert user as it's trusted
    user = User(**user)
    type_, key, data = redis.dumps(user)
    await info.context["request"].app.redis.pool.hset(type_, key, data)

    info.context["current_user"] = user

    return await next(root, info, **args)
