from itsdangerous import Serializer, BadSignature

from dixtionary.model import Context
from dixtionary.model.query import User


async def authorize(next, root, info, **args):
    if info.context.request.app.config.NO_AUTH:
        info.context = Context(
            request=info.context.request,
            current_user=User(uuid=0, name='bill')
        )
        return await next(root, info, **args)

    if 'login' == info.path[0]:
        return await next(root, info, **args)

    try:
        token = info.variable_values['token']
    except KeyError:
        msg = "token variable required for access. Try the login endpoint."
        raise ValueError(msg)

    serializer = Serializer(info.context.request.app.config.SECRET)

    try:
        user = serializer.loads(token)
    except BadSignature:
        msg = "Looks like you've been tampering with you token. Get out."
        raise ValueError(msg)

    info.context = Context(
        request=info.context.request,
        current_user=User(**user)
    )

    return await next(root, info, **args)
