from uuid import uuid4
from datetime import datetime

import graphene as g

from itsdangerous import Serializer

from .query import User, Room, Message, Turn
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
            chat=[],
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
        room_uuid = g.String(required=True)
        body = g.String(required=True)

    Output = Message

    async def mutate(self, info, room_uuid, body):
        redis = info.context["request"].app.redis
        room = await select(Room, room_uuid, conn=redis)
        msg = Message(
            uuid=uuid4().hex,
            body=body,
            time=datetime.utcnow(),
            author=info.context["current_user"],
            room=room,
        )
        room.chat.append(msg)
        await insert(msg, conn=redis)
        await update(room, conn=redis)
        return msg


class UpdateTurn(RedisUpdateMutation):
    class Arguments:
        uuid = g.ID(required=True)
        choice = g.String(required=False)
        artwork = g.JSONString(required=False)

    Output = Turn

    async def mutate_choice(self, info, uuid, choice):
        turn = await select(Turn, uuid, conn=info.context["request"].app.redis)
        user = info.context["current_user"]

        if turn.artist != user.uuid:
            raise ValueError("Not your turn to choose.")

        if choice not in turn.choices:
            raise ValueError(
                f"Not a valid choice. You must choose between {str_list(turn.choice)}."
            )

        if turn.choice:
            raise ValueError(
                f"You've already chosen {turn.choice}; "
                "You'll have to learn to live with it."
            )

        return await RedisUpdateMutation.mutate(self, info, uuid, choice=choice)

    async def mutate_artwork(self, info, uuid, artwork):
        turn = await select(Turn, uuid, conn=info.context["request"].app.redis)
        user = info.context["current_user"]

        if turn.artist != user.uuid:
            raise ValueError("Not your turn to draw.")

        if not turn.choice:
            raise ValueError(
                f"Need to choose something to draw first."
            )

        if not turn.duration:
            raise ValueError(
                "The clocks not running. Would be cheating to draw now."
            )

        return await RedisUpdateMutation.mutate(self, info, uuid, artwork=artwork)


class Mutation(g.ObjectType):
    login = Login.Field()

    insert_room = InsertRoom.Field()
    update_room = UpdateRoom.Field()
    delete_room = DeleteRoom.Field()

    insert_message = InsertMessage.Field()

    update_turn = UpdateTurn.Field()
