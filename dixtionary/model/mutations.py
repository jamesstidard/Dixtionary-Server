from uuid import uuid4

import graphene as g

from itsdangerous import Serializer

from .query import User, Room, Game


class Login(g.Mutation):
    class Arguments:
        name = g.String()

    token = g.String()

    def mutate(self, info, name):
        user = User(uuid=uuid4().hex, name=name)
        serializer = Serializer(info.context.app.config.SECRET)
        token = serializer.dumps(vars(user))
        return Login(token=token)


class InsertRoom(g.Mutation):
    class Arguments:
        name = g.String(required=True)
        password = g.String(required=False)
        capacity = g.Int(required=True, default_value=8)

    Output = Room

    def mutate(self, info, name, password, capacity):
        user = info.context.current_user
        room = Room(
            uuid=uuid4().hex,
            name=name,
            owner=user,
            password=password,
            members=[user],
            capacity=capacity,
            game=Game(
                uuid=uuid4().hex
            ),
        )
        # TODO: info.context.app.redis.set(...)
        return room


class UpdateRoom(g.Mutation):
    class Arguments:
        uuid = g.ID(required=True)
        name = g.String(required=False)
        password = g.String(required=False)
        capacity = g.Int(required=False)

    Output = Room

    def mutate(self, info, uuid, **kwargs):
        room = None  # TODO: info.context.app.redis.get(...)
        user = info.context.current_user

        if room.owner != user:
            raise ValueError("Not your room to change")

        room = Room(**vars(room), **kwargs)
        return room


class Mutation(g.ObjectType):
    login = Login.Field()
    insert_room = InsertRoom.Field()
    update_room = UpdateRoom.Field()
