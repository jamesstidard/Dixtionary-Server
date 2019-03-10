from collections import namedtuple

from sanic.request import Request

from itsdangerous import Serializer, BadSignature


def get_current_user(request: Request):
    try:
        cookie_user = request.cookies['me']
    except KeyError:
        return None

    serializer = Serializer(request.app.config.COOKIE_SECRET)

    try:
        user = serializer.loads(cookie_user)
    except BadSignature:
        return None
    else:
        CurrentUser = namedtuple('CurrentUser', user.keys())
        return CurrentUser(**user)


def set_current_user(user, *, request, response):
    try:
        user = vars(user)
    except TypeError:
        user = user._asdict()

    if user:
        serializer = Serializer(request.app.config.COOKIE_SECRET)
        response.cookies['me'] = serializer.dumps(user)
    else:
        del response.cookies['me']
