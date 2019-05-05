import inspect
from promise import Promise
from itsdangerous import Serializer, BadSignature

from dixtionary.model.query import User
from dixtionary.database import insert, exists


async def auth_user(*, token, app):
    if not token:
        return None

    token = token.replace('Bearer ', '')
    serializer = Serializer(app.config.SECRET)

    try:
        user = serializer.loads(token)
    except BadSignature:
        msg = "Looks like you've been tampering with you token. Get out."
        raise ValueError(msg)

    # maybe server database has been cleared.
    # insert user as it's trusted
    user = User(**user)

    known = await exists(User, user.uuid, conn=app.redis)
    if not known:
        await insert(user, conn=app.redis)

    return user


def auth_required(info):
    is_query = info.operation.operation == 'query'
    is_subscription = info.operation.operation == 'subscription'
    room_join = info.field_name == 'joinRoom'
    read_only = is_query or (is_subscription and not room_join)
    login = 'login' == info.path[0]

    return not (read_only or login)


async def _authorize(*, token, info):
    info.context["current_user"] = await auth_user(
        token=token,
        app=info.context["request"].app
    )

    if auth_required(info) and not info.context["current_user"]:
        msg = "token variable required for access. Try the login endpoint."
        raise ValueError(msg)


async def _authorize_ws_subscription(next, root, info, **args):
    token = info.context["connection_params"].get("authorization")
    await _authorize(token=token, info=info)

    async for msg in next(root, info, **args):
        yield msg


async def _authorize_ws_query_mutation(next, root, info, **args):
    token = info.context["connection_params"].get("authorization")
    await _authorize(token=token, info=info)

    result = next(root, info, **args)
    if inspect.isawaitable(result):
        return await result
    else:
        return result


def authorize_ws(next, root, info, **args):
    if info.operation.operation == 'subscription':
        if not str(next).startswith('Subscription.'):
            return next(root, info, **args)
        return _authorize_ws_subscription(next, root, info, **args)
    else:
        return _authorize_ws_query_mutation(next, root, info, **args)


async def authorize_http(next, root, info, **args):
    token = info.context["request"].headers.get("authorization")
    await _authorize(token=token, info=info)

    return await next(root, info, **args)
