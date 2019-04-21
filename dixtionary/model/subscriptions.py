import asyncio

import graphene as g
from itsdangerous import BadSignature, Serializer
from loguru import logger

from dixtionary.database import select, update
from dixtionary.model.query import Room, Game, Seconds, Round, Turn
from dixtionary.utils.string import underscore


async def resolve(root, info, uuids=None):
    if uuids:
        uuids = set(uuids)

    channel = underscore(info.field_name).upper()
    cls = info.return_type.graphene_type
    app = info.context["request"].app

    logger.info(f"SUBSCRIBED {channel} {id(info.context['request'])}")
    async with app.subscribe(channel)as messages:
        async for data in messages:
            logger.info(f"{channel} {id(info.context['request'])} {data}")
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


class GameSubscription(g.ObjectType):
    uuid = g.ID(required=True)
    rounds = g.List(g.ID, required=True)
    complete = g.Boolean(required=True)


class GameUpdated(GameSubscription):
    ...


class GameDeleted(GameSubscription):
    ...


class RoundSubscription(g.ObjectType):
    uuid = g.ID(required=True)
    turns = g.List(g.ID, required=True)


class RoundUpdated(RoundSubscription):
    ...


class RoundDeleted(RoundSubscription):
    ...


class TurnSubscription(g.ObjectType):
    uuid = g.ID(required=True)
    choices = g.List(g.String, required=True)
    choice = g.String(required=False)
    artist = g.Field(g.ID, required=True)
    scores = g.List(g.ID)
    remaining = Seconds(required=False)
    artwork = g.JSONString(required=False)


class TurnUpdated(TurnSubscription):
    ...


class TurnDeleted(TurnSubscription):
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


class MessageSubscription(g.ObjectType):
    uuid = g.ID(required=True)
    time = g.DateTime(required=True)
    body = g.String(required=True)
    author = g.ID(required=True)
    room = g.ID(required=True)
    correctGuess = g.Boolean(required=True)


class MessageInserted(MessageSubscription):
    ...


class ScoreSubscription(g.ObjectType):
    uuid = g.ID(required=True)
    user = g.ID(required=True)
    value = g.Int(required=True)


class ScoreInserted(ScoreSubscription):
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
    game_updated = g.Field(
        GameUpdated,
        description='The games industry doesn\'t stand still',
        uuids=g.List(g.String, required=False),
    )
    game_deleted = g.Field(
        GameDeleted,
        description='GG WP',
        uuids=g.List(g.String, required=False),
    )
    round_updated = g.Field(
        RoundUpdated,
        description='I\'m low on quips',
        uuids=g.List(g.String, required=False),
    )
    round_deleted = g.Field(
        RoundDeleted,
        description='Round and round we go',
        uuids=g.List(g.String, required=False),
    )
    turn_updated = g.Field(
        TurnUpdated,
        description='Upturned',
        token=g.String(required=True),
        uuids=g.List(g.String, required=False),
    )
    turn_deleted = g.Field(
        TurnDeleted,
        description='ok, ok, wrap it up',
        uuids=g.List(g.String, required=False),
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
        MessageInserted,
        description='What did you say?',
        room_uuid=g.String(required=False),
        token=g.String(required=False),
    )
    score_inserted = g.Field(
        ScoreInserted,
        description='Points mean prizes',
        game_uuid=g.String(required=True),
    )

    def resolve_room_inserted(root, info):
        return resolve(root, info)

    def resolve_room_updated(root, info, uuids=None):
        return resolve(root, info, uuids=uuids)

    def resolve_room_deleted(root, info, uuids=None):
        return resolve(root, info, uuids=uuids)

    async def resolve_join_room(root, info, uuid, token):
        # TODO: fix ws authorize
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

        logger.info(f"JOINED {user['name']} {room.name}")
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
            await update(room, conn=info.context["request"].app.redis)
            logger.info(f"LEFT {uuid} {id(info.context['request'])}")
            raise

    def resolve_game_updated(root, info, uuids=None):
        return resolve(root, info, uuids=uuids)

    def resolve_game_deleted(root, info, uuids=None):
        return resolve(root, info, uuids=uuids)

    def resolve_round_updated(root, info, uuids=None):
        return resolve(root, info, uuids=uuids)

    def resolve_round_deleted(root, info, uuids=None):
        return resolve(root, info, uuids=uuids)

    async def resolve_turn_updated(root, info, token, uuids=None):
        # TODO: fix ws authorize
        serializer = Serializer(info.context["request"].app.config.SECRET)

        try:
            user = serializer.loads(token)
        except BadSignature:
            msg = "Looks like you've been tampering with you token. Get out."
            raise ValueError(msg)

        async for turn in resolve(root, info, uuids=uuids):
            if turn.artist != user['uuid']:
                turn.choices = []
                turn.choice = None

            yield turn

    def resolve_turn_deleted(root, info, uuids=None):
        return resolve(root, info, uuids=uuids)

    def resolve_user_inserted(root, info):
        return resolve(root, info)

    def resolve_user_updated(root, info, uuids=None):
        return resolve(root, info, uuids=uuids)

    def resolve_user_deleted(root, info, uuids=None):
        return resolve(root, info, uuids=uuids)

    async def resolve_message_inserted(root, info, room_uuid, token=None):
        # TODO: fix ws authorize and clean up
        if token:
            serializer = Serializer(info.context["request"].app.config.SECRET)
            try:
                user = serializer.loads(token)
            except BadSignature:
                msg = "Looks like you've been tampering with you token. Get out."
                raise ValueError(msg)
        else:
            user = None

        async for message in resolve(root, info):
            if message.room == room_uuid:
                if not user or (message.correctGuess and message.author != user['uuid']):
                    message.body = '*******'
                yield message

    async def resolve_score_inserted(root, info, game_uuid):
        conn = info.context['request'].app.redis
        async for score in resolve(root, info):
            game = await select(Game, game_uuid, conn=conn)
            rounds = [await select(Round, r, conn=conn) for r in game.rounds]
            turns = [await select(Turn, t, conn=conn) for r in rounds for t in r.turns]
            scores = set(s for t in turns for s in t.scores)

            if score.uuid in scores:
                yield score
