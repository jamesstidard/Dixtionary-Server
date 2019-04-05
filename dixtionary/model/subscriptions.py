import graphene as g

from loguru import logger

from dixtionary.utils.string import underscore


async def resolve(root, info):
    ch_name = underscore(info.field_name).upper()

    logger.info(f"SUBSCRIBED {ch_name} {id(info.context['request'])}")

    cls = info.return_type.graphene_type
    app = info.context["request"].app
    channel, = await app.redis.subscribe(ch_name)

    while await channel.wait_message():
        data = await channel.get_json()
        logger.info(f"{ch_name} {id(info.context['request'])} {data}")
        yield cls(**data)


class RoomSubscription(g.ObjectType):
    uuid = g.ID(required=True)
    name = g.String(required=True)
    owner = g.ID(required=True)
    password = g.String(required=False)
    members = g.List(g.ID, required=True)
    capacity = g.Int(required=True)
    game = g.ID(required=True)
    chat = g.List(g.ID, required=True)


class RoomInserted(RoomSubscription):
    ...


class RoomUpdated(RoomSubscription):
    ...


class RoomDeleted(RoomSubscription):
    ...


class Subscription(g.ObjectType):
    room_inserted = g.Field(RoomInserted, description='New rooms you say?')
    room_updated = g.Field(RoomUpdated, description='Updated rooms? do tell...')
    room_deleted = g.Field(RoomDeleted, description='Room? Where?')

    def resolve_room_inserted(root, info):
        return resolve(root, info)

    def resolve_room_updated(root, info):
        return resolve(root, info)

    def resolve_room_deleted(root, info):
        return resolve(root, info)
