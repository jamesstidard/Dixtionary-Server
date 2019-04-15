import asyncio
import random

import graphene as g
from itsdangerous import BadSignature, Serializer
from loguru import logger

from dixtionary.database import select, update, delete
from dixtionary.model.query import Message, Room
from dixtionary.utils.string import underscore


async def resolve(root, info, uuids=None):
    ch_name = underscore(info.field_name).upper()

    logger.info(f"SUBSCRIBED {ch_name} {id(info.context['request'])}")

    cls = info.return_type.graphene_type
    app = info.context["request"].app

    if uuids:
        uuids = set(uuids)

    async with app.subscribe(ch_name)as messages:
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
    game = g.ID(required=False)
    chat = g.List(g.ID, required=True)


class RoomInserted(RoomSubscription):
    ...


class RoomUpdated(RoomSubscription):
    ...


class RoomDeleted(RoomSubscription):
    ...


class UserSubscription(g.ObjectType):
    uuid = g.ID(required=True)
    name = g.String(required=True)


class UserInserted(UserSubscription):
    ...


class UserUpdated(UserSubscription):
    ...


class UserDeleted(UserSubscription):
    ...


class Subscription(g.ObjectType):
    room_inserted = g.Field(
        RoomInserted,
        description='New rooms you say?',
    )
    room_updated = g.Field(
        RoomUpdated,
        description='Updated rooms? do tell...',
        uuids=g.List(g.String, required=False),
    )
    room_deleted = g.Field(
        RoomDeleted,
        description='Room? Where?',
        uuids=g.List(g.String, required=False),
    )
    join_room = g.Boolean(
        description='Hold on tight - if your in the room',
        uuid=g.String(required=True),
        token=g.String(required=True),
    )
    user_inserted = g.Field(
        UserInserted,
        description='New around these parts.',
    )
    user_updated = g.Field(
        UserUpdated,
        description='New year; new you.',
        uuids=g.List(g.String, required=False),
    )
    user_deleted = g.Field(
        UserDeleted,
        description='Banished',
        uuids=g.List(g.String, required=False),
    )
    message_inserted = g.Field(
        Message,
        description='What did you say?',
        room_uuid=g.String(required=False),
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

        room = await select(Room, uuid, conn=info.context["request"].app.redis)
        room.members = [*room.members, user["uuid"]]

        # set to allow same person to join the room from multiple browser sessions.
        if len(set(room.members)) > room.capacity:
            raise ValueError("Sorry, the room is full.")

        await update(room, conn=info.context["request"].app.redis)

        yield True

        try:
            while True:
                await asyncio.sleep(60)
        except Exception:
            room = await select(Room, uuid, conn=info.context["request"].app.redis)
            members = list(room.members)
            members.pop(members.index(user["uuid"]))
            room.members = members

            if len(room.members) == 0:
                # last member leaves. close room.
                await delete(room, conn=info.context["request"].app.redis)
                logger.info(f"CLOSED ROOM {room.uuid}")
            else:
                if room.owner not in room.members:
                    room.owner = random.choice(room.members)

                await update(room, conn=info.context["request"].app.redis)
                logger.info(f"LEFT {uuid} {id(info.context['request'])}")

            raise

    def resolve_user_inserted(root, info):
        return resolve(root, info)

    def resolve_user_updated(root, info, uuids=None):
        return resolve(root, info, uuids=uuids)

    def resolve_user_deleted(root, info, uuids=None):
        return resolve(root, info, uuids=uuids)

    async def resolve_message_inserted(root, info, room_uuid):
        async for message in resolve(root, info):
            if message.room == room_uuid:
                yield message
