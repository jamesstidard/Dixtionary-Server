import asyncio

import graphene as g

from .query import Room


class Subscription(g.ObjectType):
    room_inserted = g.Field(Room, description='New rooms you say?')
    room_updated = g.Field(Room, description='Updated rooms? do tell')

    async def resolve_room_inserted(root, info):
        # TODO: https://tech.webinterpret.com/redis-notifications-python/
        for i in range(5):
            yield Room(uuid=i, name='new')
            await asyncio.sleep(1.)
        yield Room(uuid=5, name='new')

    async def resolve_room_updated(root, info):
        await asyncio.sleep(10)
        for i in range(5):
            yield Room(uuid=i, name='updated')
            await asyncio.sleep(1.)
        yield Room(uuid=5, name='updated')
