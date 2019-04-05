import graphene as g

from loguru import logger


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


class RoomDeleted(RoomInserted):
    ...


class Subscription(g.ObjectType):
    room_inserted = g.Field(RoomInserted, description='New rooms you say?')
    room_updated = g.Field(RoomUpdated, description='Updated rooms? do tell...')
    room_deleted = g.Field(RoomDeleted, description='Room? Where?')

    async def resolve_room_inserted(root, info):
        logger.info(f"INSERTS SUBSCRIBED {id(info.context['request'])}")
        app = info.context["request"].app
        channel, = await app.redis.subscribe('ROOM_INSERTED')
        while await channel.wait_message():
            data = await channel.get_json()
            logger.info(f"INSERTED {id(info.context['request'])} {data}")
            yield RoomInserted(**data)

    async def resolve_room_updated(root, info):
        logger.info(f"UPDATES SUBSCRIBED {id(info.context['request'])}")
        app = info.context["request"].app
        channel, = await app.redis.subscribe('ROOM_UPDATED')
        while await channel.wait_message():
            data = await channel.get_json()
            logger.info(f"UPDATED {id(info.context['request'])} {data}")
            yield RoomUpdated(**data)

    async def resolve_room_deleted(root, info):
        logger.info(f"DELETES SUBSCRIBED {id(info.context['request'])}")
        app = info.context["request"].app
        channel, = await app.redis.subscribe('ROOM_DELETED')
        while await channel.wait_message():
            data = await channel.get_json()
            logger.info(f"DELETED {id(info.context['request'])} {data}")
            yield RoomDeleted(**data)
