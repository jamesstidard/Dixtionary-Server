import graphene as g
from graphene.types import Scalar
from graphql.language import ast

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


class RedisObjectType(g.ObjectType):
    uuid = g.ID(required=True)

    async def resolve(self, info, uuid):
        if uuid is None:
            return None

        return_type = info.return_type

        while hasattr(return_type, 'of_type'):
            return_type = return_type.of_type

        cls = return_type.graphene_type
        return await select(cls, uuid, conn=info.context["request"].app.redis)


class User(RedisObjectType):
    name = g.String(required=True)


class Score(RedisObjectType):
    user = g.Field(User, required=True)
    value = g.Int(required=True)

    async def resolve_user(self, info):
        return await User.resolve(self, info, self.user)


class Turn(RedisObjectType):
    choices = g.List(g.String, required=True)
    choice = g.String(required=False)
    artist = g.Field(User, required=True)
    scores = g.List(Score)
    remaining = Seconds(required=False)
    artwork = g.JSONString(required=False)

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
        return await User.resolve(self, info, self.artist)

    async def resolve_scores(self, info):
        return [Score.resolve(self, info, uuid) for uuid in self.scores]


class Round(RedisObjectType):
    turns = g.List(Turn, required=True)


class Game(RedisObjectType):
    rounds = g.List(Round)
    complete = g.Boolean(required=True)

    async def resolve_rounds(self, info):
        return [Round.resolve(self, info, uuid) for uuid in self.rounds]


class Message(RedisObjectType):
    time = g.DateTime(required=True)
    body = g.String(required=True)
    author = g.Field(User, required=True)
    room = g.Field('dixtionary.model.query.Room', required=True)

    async def resolve_author(self, info):
        return await User.resolve(self, info, self.author)

    async def resolve_room(self, info):
        return await Room.resolve(self, info, self.room)


class Room(RedisObjectType):
    name = g.String(required=True)
    owner = g.Field(User, required=True)
    password = g.Boolean(required=True)
    members = g.List(User, required=True)
    capacity = g.Int(required=True)
    game = g.Field(Game, required=False)
    chat = g.List(Message, required=True)

    async def resolve_password(self, info):
        return (self.password not in {None, ''})

    async def resolve_owner(self, info):
        return await User.resolve(self, info, self.owner)

    async def resolve_members(self, info):
        return [User.resolve(self, info, uuid) for uuid in self.members]

    async def resolve_game(self, info):
        return await Game.resolve(self, info, self.game)


class Query(g.ObjectType):
    me = g.Field(
        User,
        required=False,
        description='Me, myself & I',
    )
    users = g.List(
        User,
        description='Bed fellows',
        uuids=g.List(g.String, required=False),
    )
    rooms = g.List(
        Room,
        description='Game rooms',
        uuids=g.List(g.String, required=False),
    )
    games = g.List(
        Game,
        description='What do you do in a room. Play a game',
        uuids=g.List(g.String, required=False),
    )
    messages = g.List(
        Message,
        description='Chit-chat',
        room_uuid=g.String(required=True),
    )

    def resolve_me(self, info):
        return info.context["current_user"]

    async def resolve_users(self, info, uuids=None):
        if not uuids:
            uuids = await keys(User, conn=info.context["request"].app.redis)

        return [Room.resolve(self, info, uuid) for uuid in uuids]

    async def resolve_rooms(self, info, uuids=None):
        if not uuids:
            uuids = await keys(Room, conn=info.context["request"].app.redis)

        return [Room.resolve(self, info, uuid) for uuid in uuids]

    async def resolve_games(self, info, uuids=None):
        if not uuids:
            uuids = await keys(Game, conn=info.context["request"].app.redis)

        return [Game.resolve(self, info, uuid) for uuid in uuids]

    async def resolve_messages(self, info, room_uuid):
        room = await select(Room, room_uuid, conn=info.context['request'].app.redis)
        return [Message.resolve(self, info, uuid) for uuid in room.chat]
