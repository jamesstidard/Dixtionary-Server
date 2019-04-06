from itsdangerous import Serializer, BadSignature

from dixtionary.model.query import User
from dixtionary.utils import redis


async def authorize(next, root, info, **args):
    read_only = info.operation.operation == 'query'
    login = 'login' == info.path[0]

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
    await info.context["request"].app.redis.hset(type_, key, data)

    info.context["current_user"] = user

    return await next(root, info, **args)
