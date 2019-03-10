import graphene as g


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


class Room(g.ObjectType):
    uuid = g.ID(required=True)
    name = g.String(required=True)
    owner = g.Field(User, required=True)
    password = g.String(required=False)
    members = g.List(User)
    capacity = g.Int(required=True)
    game = g.Field(Game, required=True)


class Query(g.ObjectType):
    me = g.Field(User, description='The current user')
    rooms = g.List(Room)

    def resolve_me(self, info):
        user = info.context.current_user
        if user:
            return User(uuid=user.uuid, name=user.name)
        else:
            raise ValueError("No current user.")

    def resolve_rooms(self, info):
        return [
            Room(uuid=1234, name='hell', owner=User(uuid=1, name='James'), capacity=10, game=Game(uuid=1)),
            Room(uuid=1234, name='haven', owner=User(uuid=1, name='James'), capacity=10, game=Game(uuid=1)),
        ]
