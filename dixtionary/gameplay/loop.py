import random
import asyncio

from uuid import uuid4
from datetime import datetime

from loguru import logger

from dixtionary.model.query import Room, Game, Round
from dixtionary.database import select, insert


TICK_RATE_SECONDS = 1


async def start_game(app, *, room):
    with open('dixtionary/gameplay/dictionary.txt', 'r') as fp:
        dictionary = fp.read().splitlines()

    opening_round = Round(
        uuid=uuid4(),
        choices=random.choices(dictionary, k=3),
        choice=None,
        artist=random.choice(list(set(room.members))),
        scores=[],
    )
    game = Game(
        uuid=uuid4(),
        rounds=[opening_round],
    )

    await insert(game, conn=app.redis)
    await insert(opening_round, conn=app.redis)





async def tick(app, *, room):
    logger.info("room tick")

    if len(room.members) > 1 and room.game is None:
        await start_game(app, room=room)
    elif len(room.members) > 1 and room.game is not None:
        # continue with game
        pass
    elif len(room.members) < 2 and room.game:
        # end game
        pass


async def run(app, *, room_uuid):

    while True:
        started = datetime.now()
        room = await select(Room, room_uuid, conn=app.redis)

        # room has been closed.
        if not room:
            break

        await tick(app, room=room)

        delta = datetime.now() - started
        next_tick = TICK_RATE_SECONDS - delta.total_seconds()
        await asyncio.sleep(max(0, next_tick))
