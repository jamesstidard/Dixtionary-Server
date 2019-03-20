from uuid import uuid4

import graphene as g

from itsdangerous import Serializer

from .query import User, Room
from dixtionary.utils import redis


class Login(g.Mutation):
    class Arguments:
        name = g.String()

    token = g.String()

    async def mutate(self, info, **kwargs):
        user = User(uuid=uuid4().hex, **kwargs)
        serializer = Serializer(info.context.request.app.config.SECRET)
        token = serializer.dumps(vars(user))
        await info.context.request.app.redis.hmset(*redis.dumps(user))
        return Login(token=token)


class AuthenticatedArguments:
    token = g.String(required=True)


class RedisInsertMutation(g.Mutation):

    async def mutate(self, info, token, **kwargs):
        cls = info.return_type.graphene_type
        obj = cls(uuid=uuid4().hex, **kwargs)
        type_, key, data = redis.dumps(obj)
        await info.context.request.app.redis.hset(type_, key, data)
        return redis.loads(data, entity=cls)


class RedisUpdateMutation(g.Mutation):

    async def mutate(self, info, uuid, token, **kwargs):
        cls = info.return_type.graphene_type
        obj = await info.context.request.app.redis.hget(cls.__name__, uuid)
        obj = redis.loads(obj)
        obj = {**obj, **kwargs}
        obj = cls(**obj)
        await info.context.request.app.redis.hset(*redis.dumps(obj))
        return obj


class RedisDeleteMutation(g.Mutation):
    class Arguments(AuthenticatedArguments):
        uuid = g.ID(required=True)

    ok = g.Boolean()

    async def mutate(self, info, uuid, token):
        cls = info.return_type.graphene_type
        obj = await info.context.request.app.redis.hget(cls.__name__, uuid)
        obj = redis.loads(obj)
        await info.context.request.app.redis.hdel(cls.__name__, uuid)
        return cls(**obj)


class InsertRoom(RedisInsertMutation):
    class Arguments(AuthenticatedArguments):
        name = g.String(required=True)
        password = g.String(required=False, default_value=None)
        capacity = g.Int(required=False, default_value=8)

    Output = Room

    async def mutate(self, info, **kwargs):
        return await RedisInsertMutation.mutate(
            self,
            info,
            **kwargs,
            owner=info.context.current_user,
            members=[info.context.current_user],
            chat=[],
        )


class UpdateRoom(RedisUpdateMutation):
    class Arguments(AuthenticatedArguments):
        uuid = g.ID(required=True)
        name = g.String(required=False)
        password = g.String(required=False)
        capacity = g.Int(required=False)

    Output = Room

    async def mutate(self, info, uuid, **kwargs):
        data = await info.context.request.app.redis.hget(Room.__name__, uuid)
        room = Room(**redis.loads(data))
        user = info.context.current_user

        if room.owner != user.uuid:
            raise ValueError("Not your room to change")

        return await RedisUpdateMutation.mutate(self, info, uuid, **kwargs)


class DeleteRoom(RedisDeleteMutation):
    Output = Room

    async def mutate(self, info, uuid):
        data = await info.context.request.app.redis.hget(Room.__name__, uuid)
        room = Room(**redis.loads(data))
        user = info.context.current_user

        if room.owner != user.uuid:
            raise ValueError("Not your room to change")

        await info.context.app.redis.hdel(Room.__name__, uuid)
        return room


class Mutation(g.ObjectType):
    login = Login.Field()

    insert_room = InsertRoom.Field()
    update_room = UpdateRoom.Field()
    delete_room = DeleteRoom.Field()
