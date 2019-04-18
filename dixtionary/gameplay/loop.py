import random
import asyncio

from uuid import uuid4
from datetime import datetime

from loguru import logger

from dixtionary.model.query import Room, Game, Round
from dixtionary.database import select, insert, update, delete
from dixtionary.utils.asynchronous import cancel_tasks


TICK_RATE_SECONDS = 1


async def host_game(app, *, room_uuid):
    try:
        with open('dixtionary/gameplay/dictionary.txt', 'r') as fp:
            dictionary = fp.read().splitlines()

        room = await select(Room, room_uuid, conn=app.redis)

        game = Game(
            uuid=uuid4().hex,
            rounds=[],
        )
        room.game = game

        await update(room, conn=app.redis)
        await insert(game, conn=app.redis)

        for _ in range(8):
            round_ = Round(
                uuid=uuid4().hex,
                choices=random.choices(dictionary, k=3),
                choice=None,
                artist=random.choice(list(set(room.members))),
                scores=[],
            )

            game.rounds.append(round_)
            await update(game, conn=app.redis)
            await insert(round_, conn=app.redis)

            # await artist choice or leaves or timesout

            # start round timer and listen to chat messages

            # append scores as guesses come in

            while True:
                await asyncio.sleep(1)

    except asyncio.CancelledError:
        logger.warning("cleanup database and remove game from room")
        pass


# async def run(app, *, room_uuid):

#     while True:
#         started = datetime.now()
#         room = await select(Room, room_uuid, conn=app.redis)

#         # room has been closed.
#         if not room:
#             break

#         await tick(app, room=room)

#         delta = datetime.now() - started
#         next_tick = TICK_RATE_SECONDS - delta.total_seconds()
#         await asyncio.sleep(max(0, next_tick))


async def members_change(app, *, room_uuid, last_known=None):
    if last_known is None:
        last_known = {object()}

    try:
        async with app.subscribe('ROOM_UPDATED') as messages:
            async for data in messages:
                if data['uuid'] != room_uuid:
                    continue

                room = Room(**data)
                if set(room.members) != set(last_known):
                    return room

    except asyncio.CancelledError:
        pass


async def run(app, *, room_uuid):
    logger.info(f"Game loop started room {room_uuid}")
    game = None
    membership = asyncio.create_task(
        members_change(app, room_uuid=room_uuid)
    )

    pending = {membership}

    while True:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)

        [done] = done
        game_running = game in pending

        if done is membership:
            room = await done
            membership = asyncio.create_task(
                members_change(app, room_uuid=room_uuid, last_known=room.members)
            )
            pending = {*pending, membership}

            # promote new owner if they've gone
            if room.members and room.owner not in room.members:
                room.owner = random.choice(room.members)

            # user could have multiple browser tabs open
            unique_members = set(room.members)

            start_game = len(unique_members) >= 2 and not game_running
            suspend_game = len(unique_members) == 1 and game_running
            close_room = len(unique_members) == 0

            if start_game:
                logger.info(f"Game started in room {room_uuid}")
                game = asyncio.create_task(host_game(app, room_uuid=room_uuid))
                pending = {*pending, game}
            elif suspend_game:
                logger.info(f"Game suspended in room {room_uuid}")
                pending = pending - {game}
                await cancel_tasks(game)
            elif close_room:
                await cancel_tasks(pending)
                room = await select(Room, room_uuid, conn=app.redis)
                await delete(room, conn=app.redis)
                logger.info(f"Closed room {room.uuid}")
                break

        elif done is game:
            logger.info(f"Game complete, restarting {room.uuid}")
            game = asyncio.create_task(host_game(app, room_uuid=room_uuid))
            pending = {*pending, game}

    await cancel_tasks(pending)
