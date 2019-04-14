from uuid import uuid4
from datetime import datetime

import graphene as g

from itsdangerous import Serializer

from .query import User, Room, Message
from dixtionary.database import select, insert, update, delete
from dixtionary import gameplay


class Login(g.Mutation):
    class Arguments:
        name = g.String()

    token = g.String()

    async def mutate(self, info, **kwargs):
        user = User(uuid=uuid4().hex, **kwargs)
        serializer = Serializer(info.context["request"].app.config.SECRET)
        token = serializer.dumps(vars(user))
        await insert(user, conn=info.context["request"].app.redis)
        return Login(token=token)


class RedisInsertMutation(g.Mutation):

    async def mutate(self, info, **kwargs):
        cls = info.return_type.graphene_type
        obj = cls(uuid=uuid4().hex, **kwargs)
        await insert(obj, conn=info.context["request"].app.redis)
        return obj


class RedisUpdateMutation(g.Mutation):

    async def mutate(self, info, uuid, **kwargs):
        cls = info.return_type.graphene_type
        obj = await select(cls, uuid, conn=info.context["request"].app.redis)
        obj = cls(**{**vars(obj), **kwargs})
        await update(obj, conn=info.context["request"].app.redis)
        return obj


class RedisDeleteMutation(g.Mutation):
    class Arguments:
        uuid = g.ID(required=True)

    async def mutate(self, info, uuid):
        cls = info.return_type.graphene_type
        obj = await select(cls, uuid, conn=info.context["request"].app.redis)
        await delete(obj, conn=info.context["request"].app.redis)
        return obj


class InsertRoom(RedisInsertMutation):
    class Arguments:
        name = g.String(required=True)
        password = g.String(required=False, default_value=None)
        capacity = g.Int(required=False, default_value=8)

    Output = Room

    async def mutate(self, info, **kwargs):
        room = await RedisInsertMutation.mutate(
            self,
            info,
            **kwargs,
            owner=info.context["current_user"],
            members=[],
        )
        app = info.context["request"].app
        app.add_task(gameplay.loop.run(app, room_uuid=room.uuid))
        return room


class UpdateRoom(RedisUpdateMutation):
    class Arguments:
        uuid = g.ID(required=True)
        name = g.String(required=False)
        password = g.String(required=False)
        capacity = g.Int(required=False)

    Output = Room

    async def mutate(self, info, uuid, **kwargs):
        room = await select(Room, uuid, conn=info.context["request"].app.redis)
        user = info.context["current_user"]

        if room.owner != user.uuid:
            raise ValueError("Not your room to change")

        return await RedisUpdateMutation.mutate(self, info, uuid, **kwargs)


class DeleteRoom(RedisDeleteMutation):
    Output = Room

    async def mutate(self, info, uuid, **kwargs):
        room = await select(Room, uuid, conn=info.context["request"].app.redis)
        user = info.context["current_user"]

        if room.owner != user.uuid:
            raise ValueError("Not your room to change")

        return await RedisDeleteMutation.mutate(self, info, uuid)


class InsertMessage(RedisInsertMutation):
    class Arguments:
        room = g.String(required=True)
        body = g.String(required=True)

    Output = Message

    async def mutate(self, info, **kwargs):
        msg = Message(
            uuid=uuid4().hex,
            **kwargs,
            time=datetime.utcnow(),
            author=info.context["current_user"],
        )
        await insert(msg, conn=info.context["request"].app.redis)
        return msg


class Mutation(g.ObjectType):
    login = Login.Field()

    insert_room = InsertRoom.Field()
    update_room = UpdateRoom.Field()
    delete_room = DeleteRoom.Field()

    insert_message = InsertMessage.Field()
