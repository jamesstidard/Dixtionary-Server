import graphene as g

from .query import Query
from .mutations import Mutation
from .subscriptions import Subscription


def make_schema():
    return g.Schema(
        query=Query,
        mutation=Mutation,
        subscription=Subscription,
    )
