import graphene as g

from dixtionary.utils import redis


class RedisObjectType(g.ObjectType):

    async def resolve(self, info, uuid):
        cls = info.return_type.of_type.graphene_type
        data = await info.context.request.app.redis.hget(cls.__name__, uuid)
        obj = redis.loads(data)
        return cls(**obj)


class User(RedisObjectType):
    uuid = g.ID(required=True)
    name = g.String(required=True)


class Score(RedisObjectType):
    uuid = g.ID(required=True)
    user = g.Field(User, required=True)
    value = g.Int(required=True)

    async def resolve_user(self, info, uuid):
        return await User.resolve(self, info, self.user)


class Round(RedisObjectType):
    uuid = g.ID(required=True)
    choices = g.List(g.String, required=True)
    choice = g.String(required=False)
    artist = g.Field(User, required=True)
    scores = g.List(Score)

    async def resolve_artist(self, info, uuid):
        return await User.resolve(self, info, self.artist)

    async def resolve_scores(self, info, uuid):
        return [Score.resolve(self, info, uuid) for uuid in self.scores]


class Game(RedisObjectType):
    uuid = g.ID(required=True)
    rounds = g.List(Round)

    async def resolve_rounds(self, info, uuid):
        return [Round.resolve(self, info, uuid) for uuid in self.rounds]


class Message(RedisObjectType):
    uuid = g.ID(required=True)
    time = g.DateTime(required=True)
    body = g.String(required=True)


class Room(RedisObjectType):
    uuid = g.ID(required=True)
    name = g.String(required=True)
    owner = g.Field(User, required=True)
    password = g.String(required=False)
    members = g.List(User, required=True)
    capacity = g.Int(required=True)
    game = g.Field(Game, required=True)
    chat = g.List(Message, required=True)

    async def resolve_owner(self, info):
        return await User.resolve(self, info, self.owner)

    async def resolve_members(self, info):
        return [User.resolve(self, info, uuid) for uuid in self.members]

    async def resolve_game(self, info):
        return await Game.resolve(self, info, self.game)

    async def resolve_chat(self, info):
        return [Message.resolve(self, info, uuid) for uuid in self.chat]


class Query(g.ObjectType):
    me = g.Field(User, description='Who are you?')
    rooms = g.List(Room, description='Game rooms')

    def resolve_me(self, info):
        user = info.context.current_user
        if user:
            return User(uuid=user.uuid, name=user.name)
        else:
            raise ValueError("No current user.")

    async def resolve_rooms(self, info):
        uuids = await info.context.request.app.redis.hkeys(str(Room))
        return [Room.resolve(self, info, uuid) for uuid in uuids]
