from typing import NamedTuple

import graphene as g

from sanic.request import Request

from .query import Query, User
from .mutations import Mutation


class Context(NamedTuple):
    request: Request
    current_user: User


def make_schema():
    return g.Schema(
        query=Query,
        mutation=Mutation,
    )
