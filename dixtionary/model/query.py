import graphene as g
from graphql.type.definition import GraphQLList

from dixtionary.utils import redis


class RedisObjectType(g.ObjectType):
    uuid = g.ID(required=True)

    async def resolve(self, info, uuid):
        cls = info.return_type.of_type
        if isinstance(cls, GraphQLList):
            cls = cls.of_type
        cls = cls.graphene_type
        data = await info.context["request"].app.redis.hget(cls.__name__, uuid)
        obj = redis.loads(data)
        return cls(**obj)


class User(RedisObjectType):
    name = g.String(required=True)


class Score(RedisObjectType):
    user = g.Field(User, required=True)
    value = g.Int(required=True)

    async def resolve_user(self, info):
        return await User.resolve(self, info, self.user)


class Round(RedisObjectType):
    choices = g.List(g.String, required=True)
    choice = g.String(required=False)
    artist = g.Field(User, required=True)
    scores = g.List(Score)

    async def resolve_artist(self, info):
        return await User.resolve(self, info, self.artist)

    async def resolve_scores(self, info):
        return [Score.resolve(self, info, uuid) for uuid in self.scores]


class Game(RedisObjectType):
    rounds = g.List(Round)

    async def resolve_rounds(self, info):
        return [Round.resolve(self, info, uuid) for uuid in self.rounds]


class Message(RedisObjectType):
    time = g.DateTime(required=True)
    body = g.String(required=True)


class Room(RedisObjectType):
    name = g.String(required=True)
    owner = g.Field(User, required=True)
    password = g.Boolean(required=True)
    members = g.List(User, required=True)
    capacity = g.Int(required=True)
    game = g.Field(Game, required=True)
    chat = g.List(Message, required=True)

    async def resolve_password(self, info):
        return (self.password not in {None, ''})

    async def resolve_owner(self, info):
        return await User.resolve(self, info, self.owner)

    async def resolve_members(self, info):
        print(self.members)
        return [User.resolve(self, info, uuid) for uuid in self.members]

    async def resolve_game(self, info):
        return await Game.resolve(self, info, self.game)

    async def resolve_chat(self, info):
        return [Message.resolve(self, info, uuid) for uuid in self.chat]


class Query(g.ObjectType):
    me = g.Field(User, description='Who are you?')
    rooms = g.List(Room, description='Game rooms', uuids=g.List(g.String, required=False))

    def resolve_me(self, info):
        user = info.context["current_user"]
        if user:
            return User(uuid=user.uuid, name=user.name)
        else:
            raise ValueError("No current user.")

    async def resolve_rooms(self, info, uuids=None):
        if not uuids:
            uuids = await info.context["request"].app.redis.hkeys(str(Room))

        return [Room.resolve(self, info, uuid) for uuid in uuids]
