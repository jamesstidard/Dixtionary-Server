from uuid import uuid4

import graphene as g

from .query import User


class Login(g.Mutation):
    class Arguments:
        name = g.String()

    me = g.Field(lambda: User)

    def mutate(self, info, name):
        user = User(uuid=uuid4().hex, name=name)
        info.context.current_user = user
        return Login(me=user)


class Mutation(g.ObjectType):
    login = Login.Field()
