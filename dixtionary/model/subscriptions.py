import asyncio

import graphene as g

from loguru import logger

from itsdangerous import Serializer, BadSignature

from dixtionary.utils.string import underscore
from dixtionary.model.query import Room
from dixtionary.utils import redis


async def resolve(root, info, uuids=None):
    ch_name = underscore(info.field_name).upper()

    if uuids:
        uuids = set(uuids)

    logger.info(f"SUBSCRIBED {ch_name} {id(info.context['request'])}")

    cls = info.return_type.graphene_type
    app = info.context["request"].app

    async with app.redis.subscribe(ch_name)as messages:
        async for data in messages:
            logger.info(f"{ch_name} {id(info.context['request'])} {data}")
            obj = cls(**data)

            if uuids and obj.uuid in uuids:
                yield obj
            elif not uuids:
                yield obj


class RoomSubscription(g.ObjectType):
    uuid = g.ID(required=True)
    name = g.String(required=True)
    owner = g.ID(required=True)
    password = g.String(required=False)
    members = g.List(g.ID, required=True)
    capacity = g.Int(required=True)
    game = g.ID(required=True)
    chat = g.List(g.ID, required=True)


class RoomInserted(RoomSubscription):
    ...


class RoomUpdated(RoomSubscription):
    ...


class RoomDeleted(RoomSubscription):
    ...


class Subscription(g.ObjectType):
    room_inserted = g.Field(
        RoomInserted,
        description='New rooms you say?'
    )
    room_updated = g.Field(
        RoomUpdated,
        description='Updated rooms? do tell...',
        uuids=g.List(g.String, required=False)
    )
    room_deleted = g.Field(
        RoomDeleted,
        description='Room? Where?',
        uuids=g.List(g.String, required=False)
    )
    join_room = g.Boolean(
        description='Hold on tight - if your in the room',
        uuid=g.String(required=True),
        token=g.String(required=True),
    )

    def resolve_room_inserted(root, info):
        return resolve(root, info)

    def resolve_room_updated(root, info, uuids=None):
        return resolve(root, info, uuids=uuids)

    def resolve_room_deleted(root, info, uuids=None):
        return resolve(root, info, uuids=uuids)

    async def resolve_join_room(root, info, uuid, token):
        logger.info(f"JOINED {uuid} {id(info.context['request'])}")

        serializer = Serializer(info.context["request"].app.config.SECRET)

        try:
            user = serializer.loads(token)
        except BadSignature:
            msg = "Looks like you've been tampering with you token. Get out."
            raise ValueError(msg)

        data = await info.context["request"].app.redis.pool.hget(Room.__name__, uuid)
        room = Room(**redis.loads(data))
        room.members = [*room.members, user["uuid"]]

        type_, key, data = redis.dumps(room)
        await info.context["request"].app.redis.pool.hset(type_, key, data)
        await info.context["request"].app.redis.pool.publish(f"{type_}_updated".upper(), data)

        yield True

        try:
            while True:
                await asyncio.sleep(60)
        except Exception:
            data = await info.context["request"].app.redis.pool.hget(Room.__name__, uuid)
            room = Room(**redis.loads(data))
            members = list(room.members)
            members.pop(members.index(user["uuid"]))
            room.members = members
            type_, key, data = redis.dumps(room)
            await info.context["request"].app.redis.pool.hset(type_, key, data)
            await info.context["request"].app.redis.pool.publish(f"{type_}_updated".upper(), data)
            logger.info(f"LEFT {uuid} {id(info.context['request'])}")
            raise
