from uuid import uuid4

import graphene as g

from sanic.request import Request

from .query import User


class Login(g.Mutation):
    class Arguments:
        name = g.String()

    me = g.Field(lambda: User)

    def mutate(self, info, name):
        user = User(uuid=uuid4().hex, name=name)
        request: Request = info.context
        return Login(me=user)


class Mutation(g.ObjectType):
    login = Login.Field()
