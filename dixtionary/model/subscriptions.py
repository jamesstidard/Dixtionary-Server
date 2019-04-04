import asyncio

import graphene as g


class RoomInserted(g.ObjectType):
    uuid = g.ID(required=True)
    name = g.String(required=True)
    owner = g.ID(required=True)
    password = g.String(required=False)
    members = g.List(g.ID, required=True)
    capacity = g.Int(required=True)
    game = g.ID(required=True)
    chat = g.List(g.ID, required=True)


class RoomUpdated(RoomInserted):
    ...


class Subscription(g.ObjectType):
    room_inserted = g.Field(RoomInserted, description='New rooms you say?')
    room_updated = g.Field(RoomUpdated, description='Updated rooms? do tell')

    async def resolve_room_inserted(root, info):
        app = info.context["request"].app
        sub = await app.redis.subscribe('__keyspace@0__:*')
        channel = sub[0]
        while await channel.wait_message():
            msg = await channel.get()
            print(msg)
            yield msg
        # # TODO: https://tech.webinterpret.com/redis-notifications-python/
        # for i in range(5):
        #     yield RoomInserted(uuid=i, name='new')
        #     await asyncio.sleep(1.)
        # yield RoomInserted(uuid=5, name='new')

    async def resolve_room_updated(root, info):
        await asyncio.sleep(10)
        for i in range(5):
            yield RoomUpdated(uuid=i, name='updated')
            await asyncio.sleep(1.)
        yield RoomUpdated(uuid=5, name='updated')
