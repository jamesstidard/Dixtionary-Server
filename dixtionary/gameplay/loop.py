import asyncio

from datetime import datetime

from loguru import logger

from dixtionary.model.query import Room
from dixtionary.utils import redis


TICK_RATE_SECONDS = 1


async def tick(app, *, room):
    logger.info("room tick")


async def run(app, *, room_uuid):

    while True:
        started = datetime.now()
        room = await app.redis.pool.hget('Room', room_uuid)

        # room has been closed.
        if not room:
            break

        room = Room(**redis.loads(room))
        await tick(app, room=room)

        delta = datetime.now() - started
        next_tick = TICK_RATE_SECONDS - delta.total_seconds()
        await asyncio.sleep(max(0, next_tick))
