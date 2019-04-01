from typing import NamedTuple, Optional

import graphene as g

from sanic.request import Request

from .query import Query, User
from .mutations import Mutation
from .subscriptions import Subscription


class Context(NamedTuple):
    request: Request
    current_user: Optional[User] = None


def make_schema():
    return g.Schema(
        query=Query,
        mutation=Mutation,
        subscription=Subscription,
    )
