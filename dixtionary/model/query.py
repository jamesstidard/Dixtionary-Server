import graphene as g
from graphene.types import Scalar
from graphql.language import ast

from loguru import logger

from dixtionary.database import select, keys


class Seconds(Scalar):
    @staticmethod
    def serialize(value):
        return value

    @staticmethod
    def parse_literal(node):
        if isinstance(node, ast.IntValue):
            return node.value

    @staticmethod
    def parse_value(value):
        return value


class User(g.ObjectType):
    uuid = g.ID(required=True)
    name = g.String(required=True)

    async def resolve(self, info):
        conn = info.context["request"].app.redis
        return await select(User, self.uuid, conn=conn)


class Score(g.ObjectType):
    uuid = g.ID(required=True)
    user = g.Field(User, required=True)
    value = g.Int(required=True)

    async def resolve(self, info):
        conn = info.context["request"].app.redis
        return await select(User, self.uuid, conn=conn)

    async def resolve_user(self, info):
        conn = info.context["request"].app.redis
        return await select(User, self.user, conn=conn)


class Turn(g.ObjectType):
    uuid = g.ID(required=True)
    choices = g.List(g.String, required=True)
    choice = g.String(required=False)
    artist = g.Field(User, required=True)
    scores = g.List(Score)
    remaining = Seconds(required=False)
    artwork = g.JSONString(required=False)

    async def resolve(self, info):
        logger.warning(self.uuid)
        conn = info.context["request"].app.redis
        turn = await select(Turn, self.uuid, conn=conn)
        logger.warning(turn)
        return turn

    def resolve_choice(self, info):
        user = info.context["current_user"]
        if user and user.uuid == self.artist:
            return self.choice
        else:
            return None

    def resolve_choices(self, info):
        user = info.context["current_user"]
        if user and user.uuid == self.artist:
            return self.choices
        else:
            return []

    async def resolve_artist(self, info):
        conn = info.context["request"].app.redis
        return await select(User, self.artist, conn=conn)

    async def resolve_scores(self, info):
        conn = info.context["request"].app.redis
        return [await select(Score, uuid, conn=conn) for uuid in self.scores]


class Round(g.ObjectType):
    uuid = g.ID(required=True)
    turns = g.List(Turn, required=True)

    async def resolve(self, info):
        conn = info.context["request"].app.redis
        return await select(Round, self.uuid, conn=conn)

    async def resolve_turns(self, info):
        conn = info.context["request"].app.redis
        return [await select(Turn, uuid, conn=conn) for uuid in self.turns]


class Game(g.ObjectType):
    uuid = g.ID(required=True)
    rounds = g.List(Round)
    complete = g.Boolean(required=True)

    async def resolve(self, info):
        conn = info.context["request"].app.redis
        return await select(Game, self.uuid, conn=conn)

    async def resolve_rounds(self, info):
        conn = info.context["request"].app.redis
        return [await select(Round, uuid, conn=conn) for uuid in self.rounds]


class Message(g.ObjectType):
    uuid = g.ID(required=True)
    time = g.DateTime(required=True)
    body = g.String(required=True)
    author = g.Field(User, required=True)
    room = g.Field("dixtionary.model.query.Room", required=True)
    correctGuess = g.Boolean(required=True)

    async def resolve(self, info):
        conn = info.context["request"].app.redis
        return await select(Message, self.uuid, conn=conn)

    async def resolve_body(self, info):
        user = info.context["current_user"]
        if self.correctGuess and self.author != user.uuid:
            return "*******"
        else:
            return self.body

    async def resolve_author(self, info):
        conn = info.context["request"].app.redis
        return await select(User, self.author, conn=conn)

    async def resolve_room(self, info):
        conn = info.context["request"].app.redis
        return await select(Room, self.room, conn=conn)


class Room(g.ObjectType):
    uuid = g.ID(required=True)
    name = g.String(required=True)
    owner = g.Field(User, required=True)
    invite_only = g.Boolean(required=True)
    invite_code = g.String(required=False)
    members = g.List(User, required=True)
    capacity = g.Int(required=True)
    game = g.Field(Game, required=False)
    chat = g.List(Message, required=True)

    async def resolve(self, info):
        conn = info.context["request"].app.redis
        return await select(Room, self.uuid, conn=conn)

    async def resolve_invite_only(self, info):
        return self.invite_code not in {None, ""}

    async def resolve_invite_code(self, info):
        user = info.context["current_user"]
        if user.uuid in self.members or user.uuid == self.owner:
            return self.invite_code

    async def resolve_owner(self, info):
        conn = info.context["request"].app.redis
        return await select(User, self.owner, conn=conn)

    async def resolve_members(self, info):
        conn = info.context["request"].app.redis
        return [await select(User, uuid, conn=conn) for uuid in self.members]

    async def resolve_game(self, info):
        if self.game:
            conn = info.context["request"].app.redis
            return await select(Game, self.game, conn=conn)


class Query(g.ObjectType):
    me = g.Field(User, required=False, description="Me, myself & I")
    users = g.List(
        User, description="Bed fellows", uuids=g.List(g.String, required=False)
    )
    rooms = g.List(
        Room, description="Game rooms", uuids=g.List(g.String, required=False)
    )
    games = g.List(
        Game,
        description="What do you do in a room. Play a game",
        uuids=g.List(g.String, required=False),
    )
    rounds = g.List(
        Round, description="ding ding ding", uuids=g.List(g.String, required=False)
    )
    turns = g.List(
        Turn, description="after you", uuids=g.List(g.String, required=False)
    )
    messages = g.List(
        Message, description="Chit-chat", room_uuid=g.String(required=True)
    )
    scores = g.List(
        Score, description="Everything's a compition", game_uuid=g.String(required=True)
    )

    def resolve_me(self, info):
        return info.context["current_user"]

    async def resolve_users(self, info, uuids=None):
        conn = info.context["request"].app.redis
        if uuids is None:
            uuids = await keys(User, conn=conn)

        return [await select(User, uuid, conn=conn) for uuid in uuids]

    async def resolve_rooms(self, info, uuids=None):
        conn = info.context["request"].app.redis
        if uuids is None:
            uuids = await keys(Room, conn=conn)

        return [await select(Room, uuid, conn=conn) for uuid in uuids]

    async def resolve_games(self, info, uuids=None):
        conn = info.context["request"].app.redis
        if uuids is None:
            uuids = await keys(Game, conn=conn)

        return [await select(Game, uuid, conn=conn) for uuid in uuids]

    async def resolve_rounds(self, info, uuids=None):
        conn = info.context["request"].app.redis
        if uuids is None:
            uuids = await keys(Round, conn=conn)

        return [await select(Round, uuid, conn=conn) for uuid in uuids]

    async def resolve_turns(self, info, uuids=None):
        conn = info.context["request"].app.redis
        if uuids is None:
            uuids = await keys(Turn, conn=conn)

        turns = [await select(Turn, uuid, conn=conn) for uuid in uuids]
        return turns

    async def resolve_messages(self, info, room_uuid):
        conn = info.context["request"].app.redis
        room = await select(Room, room_uuid, conn=conn)
        return [await select(Message, uuid, conn=conn) for uuid in room.chat]

    async def resolve_scores(self, info, game_uuid):
        with await info.context["request"].app.redis as conn:
            game = await select(Game, game_uuid, conn=conn)
            rounds = [await select(Round, r, conn=conn) for r in game.rounds]
            turns = [await select(Turn, t, conn=conn) for r in rounds for t in r.turns]
            scores = [
                await select(Score, s, conn=conn) for t in turns for s in t.scores
            ]

        return scores
