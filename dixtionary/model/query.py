import graphene as g

from dixtionary.utils import redis


class User(g.ObjectType):
    uuid = g.ID(required=True)
    name = g.String(required=True)


class Score(g.ObjectType):
    uuid = g.ID(required=True)
    user = g.Field(User, required=True)
    value = g.Int(required=True)


class Round(g.ObjectType):
    uuid = g.ID(required=True)
    choices = g.List(g.String, required=True)
    choice = g.String(required=False)
    artist = g.Field(User, required=True)
    scores = g.List(Score)


class Game(g.ObjectType):
    uuid = g.ID(required=True)
    rounds = g.List(Round)


class Message(g.ObjectType):
    uuid = g.ID(required=True)
    time = g.DateTime(required=True)
    body = g.String(required=True)


class Room(g.ObjectType):
    uuid = g.ID(required=True)
    name = g.String(required=True)
    owner = g.Field(User, required=True)
    password = g.String(required=False)
    members = g.List(User)
    capacity = g.Int(required=True)
    game = g.Field(Game, required=True)
    chat = g.List(Message)

    async def resolve(self, info, uuid):
        data = await info.context.request.app.redis.hget(str(Room), uuid)
        room = redis.loads(data)
        return Room(**room)


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
        return [Room().resolve(info, uuid) for uuid in uuids]
