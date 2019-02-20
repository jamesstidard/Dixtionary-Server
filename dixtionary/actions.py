import json

import graphene as g


class User(g.ObjectType):
    id = g.ID(required=True)
    name = g.String(required=True)


class Score(g.ObjectType):
    id = g.ID(required=True)
    user = g.Field(User, required=True)
    value = g.Int(required=True)


class Round(g.ObjectType):
    id = g.ID(required=True)
    choices = g.List(g.String, required=True)
    chosen_word = g.String(required=False)
    artist = g.Field(User, required=True)
    scores = g.List(Score)


class Game(g.ObjectType):
    id = g.ID(required=True)
    rounds = g.List(Round)


class Room(g.ObjectType):
    id = g.ID(required=True)
    name = g.String(required=True)
    owner = g.Field(User, required=True)
    password = g.String(required=False)
    members = g.List(User)
    capacity = g.Int(required=True)
    game = g.Field(Game, required=True)


class Query(g.ObjectType):
    me = g.Field(User)
    rooms = g.List(Room)

    def resolve_me(self, info):
        return User(id=1234, name='James')

    def resolve_rooms(self, info):
        return [
            Room(id=1234, name='hell', owner=User(id=1, name='James'), capacity=10, game=Game(id=1)),
            Room(id=1234, name='haven', owner=User(id=1, name='James'), capacity=10, game=Game(id=1)),
        ]


schema = g.Schema(query=Query, auto_camelcase=False)
print(schema)

result = schema.execute('{ me { id, name }, rooms { name, capacity } }')
print(json.dumps(result.data, indent=2))  # "Hello stranger"
#
# # or passing the argument in the query
# result = schema.execute('{ hello (argument: "graph") }')
# print(result.data['hello']) # "Hello graph"
