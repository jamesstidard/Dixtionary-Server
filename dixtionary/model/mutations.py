from uuid import uuid4
from datetime import datetime

import graphene as g

from itsdangerous import Serializer

from .query import User, Room, Message
from dixtionary.utils import redis


class Login(g.Mutation):
    class Arguments:
        name = g.String()

    token = g.String()

    async def mutate(self, info, **kwargs):
        user = User(uuid=uuid4().hex, **kwargs)
        serializer = Serializer(info.context["request"].app.config.SECRET)
        token = serializer.dumps(vars(user))
        type_, key, data = redis.dumps(user)
        await info.context["request"].app.redis.pool.hmset(type_, key, data)
        await info.context["request"].app.redis.publish(f"user_inserted", user)
        return Login(token=token)


class RedisInsertMutation(g.Mutation):

    async def mutate(self, info, **kwargs):
        cls = info.return_type.graphene_type
        obj = cls(uuid=uuid4().hex, **kwargs)
        type_, key, data = redis.dumps(obj)
        await info.context["request"].app.redis.pool.hset(type_, key, data)
        await info.context["request"].app.redis.publish(f"{type_}_inserted", obj)
        return redis.loads(data, entity=cls)


class RedisUpdateMutation(g.Mutation):

    async def mutate(self, info, uuid, **kwargs):
        cls = info.return_type.graphene_type
        obj = await info.context["request"].app.redis.pool.hget(cls.__name__, uuid)
        obj = redis.loads(obj)
        obj = {**obj, **kwargs}
        obj = cls(**obj)
        type_, key, data = redis.dumps(obj)
        await info.context["request"].app.redis.pool.hset(type_, key, data)
        await info.context["request"].app.redis.publish(f"{type_}_updated", obj)
        return obj


class RedisDeleteMutation(g.Mutation):
    class Arguments:
        uuid = g.ID(required=True)

    async def mutate(self, info, uuid):
        cls = info.return_type.graphene_type
        data = await info.context["request"].app.redis.pool.hget(cls.__name__, uuid)
        obj = redis.loads(data)
        await info.context["request"].app.redis.pool.hdel(cls.__name__, uuid)
        await info.context["request"].app.redis.publish(f"{cls.__name__}_deleted", obj)
        return cls(**obj)


class InsertRoom(RedisInsertMutation):
    class Arguments:
        name = g.String(required=True)
        password = g.String(required=False, default_value=None)
        capacity = g.Int(required=False, default_value=8)

    Output = Room

    async def mutate(self, info, **kwargs):
        return await RedisInsertMutation.mutate(
            self,
            info,
            **kwargs,
            owner=info.context["current_user"],
            members=[],
        )


class UpdateRoom(RedisUpdateMutation):
    class Arguments:
        uuid = g.ID(required=True)
        name = g.String(required=False)
        password = g.String(required=False)
        capacity = g.Int(required=False)

    Output = Room

    async def mutate(self, info, uuid, **kwargs):
        data = await info.context["request"].app.redis.pool.hget(Room.__name__, uuid)
        room = Room(**redis.loads(data))
        user = info.context["current_user"]

        if room.owner != user.uuid:
            raise ValueError("Not your room to change")

        return await RedisUpdateMutation.mutate(self, info, uuid, **kwargs)


class DeleteRoom(RedisDeleteMutation):
    Output = Room

    async def mutate(self, info, uuid, **kwargs):
        data = await info.context["request"].app.redis.pool.hget(Room.__name__, uuid)
        room = Room(**redis.loads(data))
        user = info.context["current_user"]

        if room.owner != user.uuid:
            raise ValueError("Not your room to change")

        return await RedisDeleteMutation.mutate(self, info, uuid)


class InsertMessage(RedisInsertMutation):
    class Arguments:
        room = g.String(required=True)
        body = g.String(required=True)

    Output = Message

    async def mutate(self, info, room, body):
        msg = Message(
            uuid=uuid4().hex,
            room=room,
            body=body,
            time=datetime.utcnow(),
            author=info.context["current_user"]
        )
        type_, _, data = redis.dumps(msg)
        await info.context["request"].app.redis.publish(f"{type_}_inserted", msg)
        return msg


class Mutation(g.ObjectType):
    login = Login.Field()

    insert_room = InsertRoom.Field()
    update_room = UpdateRoom.Field()
    delete_room = DeleteRoom.Field()

    insert_message = InsertMessage.Field()
