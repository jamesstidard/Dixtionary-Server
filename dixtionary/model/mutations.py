from uuid import uuid4
from datetime import datetime

import graphene as g

from fuzzywuzzy import fuzz
from itsdangerous import Serializer

from .query import User, Room, Message, Turn, Score, Game, Round
from dixtionary.database import select, insert, update, delete
from dixtionary import gameplay
from dixtionary.utils.string import str_list


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
        invite_only = g.Boolean(required=False, default_value=False)
        capacity = g.Int(required=False, default_value=8)

    Output = Room

    async def mutate(self, info, invite_only=False, **kwargs):
        room = await RedisInsertMutation.mutate(
            self,
            info,
            **kwargs,
            invite_only=invite_only,
            invite_code=uuid4().hex if invite_only else None,
            owner=info.context["current_user"].uuid,
            members=[],
            chat=[],
        )
        app = info.context["request"].app
        app.add_task(gameplay.loop.run(app, room_uuid=room.uuid))
        return room


class UpdateRoom(RedisUpdateMutation):
    class Arguments:
        uuid = g.String(required=True)
        name = g.String(required=False)
        invite_only = g.Boolean(required=False)
        capacity = g.Int(required=False)

    Output = Room

    async def mutate(self, info, uuid, invite_only=None, **kwargs):
        room = await select(Room, uuid, conn=info.context["request"].app.redis)
        user = info.context["current_user"]

        if room.owner != user.uuid:
            raise ValueError("Not your room to change")

        if invite_only is True:
            invite_code = uuid4().hex
        elif invite_only is False:
            invite_code = None
        else:
            invite_only = room.invite_only

        return await RedisUpdateMutation.mutate(
            self, info, uuid, invite_only=invite_only, invite_code=invite_code, **kwargs,
        )


class DeleteRoom(RedisDeleteMutation):
    Output = Room

    async def mutate(self, info, uuid, **kwargs):
        room = await select(Room, uuid, conn=info.context["request"].app.redis)
        user = info.context["current_user"]

        if room.owner != user.uuid:
            raise ValueError("Not your room to change")

        return await RedisDeleteMutation.mutate(self, info, uuid)


async def current_turn(room_uuid, *, conn):
    room = await select(Room, room_uuid, conn=conn)
    if room.game:
        game = await select(Game, room.game, conn=conn)
        if game.rounds:
            round_ = await select(Round, game.rounds[-1], conn=conn)
            if round_.turns:
                return await select(Turn, round_.turns[-1], conn=conn)


class InsertMessage(RedisInsertMutation):
    class Arguments:
        room_uuid = g.String(required=True)
        body = g.String(required=True)

    Output = Message

    async def mutate(self, info, room_uuid, body):
        redis = info.context["request"].app.redis
        user = info.context["current_user"]

        correct = False
        turn = await current_turn(room_uuid=room_uuid, conn=redis)
        correct = (
            turn and
            turn.choice and
            fuzz.ratio(turn.choice.lower(), body.lower()) >= 95
        )

        if correct and turn.artist == user.uuid:
            raise ValueError("Don't give way the answer")

        if correct:
            user_score = Score(
                uuid=uuid4().hex,
                user=user,
                value=1,
            )
            artist_score = Score(
                uuid=uuid4().hex,
                user=turn.artist,
                value=1
            )
            turn.scores += [user_score, artist_score]
            await insert(user_score, conn=redis)
            await insert(artist_score, conn=redis)
            await update(turn, conn=redis)

        room = await select(Room, room_uuid, conn=redis)
        msg = Message(
            uuid=uuid4().hex,
            body=body,
            time=datetime.utcnow(),
            author=user,
            room=room,
            correctGuess=correct
        )

        room.chat.append(msg)
        await insert(msg, conn=redis)
        await update(room, conn=redis)
        return msg


UNTOUCHED = object()


class UpdateTurn(RedisUpdateMutation):
    class Arguments:
        uuid = g.String(required=True)
        choice = g.String(required=False)
        artwork = g.JSONString(required=False)

    Output = Turn

    async def mutate(self, info, uuid, choice=UNTOUCHED, artwork=UNTOUCHED):
        turn = await select(Turn, uuid, conn=info.context["request"].app.redis)
        user = info.context["current_user"]

        if choice is not UNTOUCHED:
            if turn.artist != user.uuid:
                raise ValueError("Not your turn to choose.")

            if choice not in turn.choices:
                raise ValueError(
                    f"Not a valid choice. You must choose between {str_list(turn.choices)}."
                )

            if turn.choice:
                raise ValueError(
                    f"You've already chosen {turn.choice}; "
                    "You'll have to learn to live with it."
                )
        else:
            choice = turn.choice

        if artwork is not UNTOUCHED:
            if turn.artist != user.uuid:
                raise ValueError("Not your turn to draw.")

            if not turn.choice:
                raise ValueError(
                    f"Need to choose something to draw first."
                )

            if not turn.remaining:
                raise ValueError(
                    "The clocks not running. Would be cheating to draw now."
                )
        else:
            artwork = turn.artwork

        return await RedisUpdateMutation.mutate(
            self, info, uuid, choice=choice, artwork=artwork
        )


class Mutation(g.ObjectType):
    login = Login.Field()

    insert_room = InsertRoom.Field()
    update_room = UpdateRoom.Field()
    delete_room = DeleteRoom.Field()

    insert_message = InsertMessage.Field()

    update_turn = UpdateTurn.Field()
