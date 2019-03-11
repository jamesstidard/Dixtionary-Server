from uuid import uuid4

import graphene as g

from itsdangerous import Serializer

from .query import User


class Login(g.Mutation):
    class Arguments:
        name = g.String()

    token = g.String()

    def mutate(self, info, name):
        user = User(uuid=uuid4().hex, name=name)
        serializer = Serializer(info.context.app.config.COOKIE_SECRET)
        token = serializer.dumps(vars(user))
        return Login(token=token)


class Mutation(g.ObjectType):
    login = Login.Field()
