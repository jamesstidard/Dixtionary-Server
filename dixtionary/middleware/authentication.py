from itsdangerous import Serializer, BadSignature

from dixtionary.model import Context
from dixtionary.model.query import User


def authorize(next, root, info, **args):
    if 'login' == info.path[0]:
        return next(root, info, **args)

    if 'token' not in info.variable_values:
        raise ValueError(
            'token variable required for access. '
            'Try the login endpoint.'
        )

    token = info.variable_values['token']
    serializer = Serializer(info.context.request.app.config.COOKIE_SECRET)

    try:
        user = serializer.loads(token)
    except BadSignature:
        raise ValueError(
            "Looks like you've been tampering with you token. Get out."
        )

    info.context = Context(
        request=info.context.request,
        current_user=User(**user)
    )

    return next(root, info, **args)
