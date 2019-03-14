from typing import NamedTuple, Optional

import graphene as g

from sanic.request import Request

from .query import Query, User
from .mutations import Mutation


class Context(NamedTuple):
    request: Request
    current_user: Optional[User] = None


def make_schema():
    return g.Schema(
        query=Query,
        mutation=Mutation,
    )
