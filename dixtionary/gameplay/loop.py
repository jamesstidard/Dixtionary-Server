import random
import asyncio

from uuid import uuid4

from loguru import logger

from dixtionary.model.query import Room, Game, Round, Turn
from dixtionary.database import select, insert, update, delete
from dixtionary.utils.asynchronous import cancel_tasks


with open('dixtionary/gameplay/dictionary.txt', 'r') as fp:
    DICTIONARY = fp.read().splitlines()


async def artist_chooses(app, *, round_uuid):
    round_ = await select(Room, round_uuid, conn=app.redis)

    if round_.choice:
        return round_.choice

    async with app.subscribe('ROUND_UPDATED') as messages:
        async for data in messages:
            round_ = Round(**data)

            if round_.uuid == round_uuid and round_.choice:
                return round_.choice


async def next_turn(app, *, room_uuid, round_uuid):
    while True:
        room = await select(Room, room_uuid, conn=app.redis)
        round_ = await select(Round, round_uuid, conn=app.redis)
        turns = [await select(Turn, t, conn=app.redis) for t in round_.turns]
        played = (t.artist for t in turns)
        to_play = set(room.members) - set(played)

        if not to_play:
            break

        # priorities based on order the user joined
        next_artist, *_ = sorted(to_play, key=room.members.index)

        yield Turn(
            uuid=uuid4().hex,
            choices=random.choices(DICTIONARY, k=3),
            choice=None,
            artist=next_artist,
            scores=[],
        )


async def host_game(app, *, room_uuid):
    try:
        room = await select(Room, room_uuid, conn=app.redis)

        game = Game(
            uuid=uuid4().hex,
            rounds=[],
        )
        room.game = game

        await update(room, conn=app.redis)
        await insert(game, conn=app.redis)

        for round_number in range(1, 9):
            logger.info(f"STARTING ROUND {round_number} {room_uuid}")
            round_ = Round(
                uuid=uuid4().hex,
                turns=[],
            )

            game.rounds.append(round_)
            await insert(round_, conn=app.redis)
            await update(game, conn=app.redis)

            async for turn in next_turn(app, room_uuid=room.uuid, round_uuid=round_.uuid):
                logger.info(f"TURN {turn.artist} {room_uuid}")
                round_.turns.append(turn)
                await insert(turn, conn=app.redis)
                await update(round_, conn=app.redis)

                await asyncio.sleep(10)

                # try:
                #     choice = await artist_choice(turn_uuid=turn_uuid, timeout=10)
                # except ConnectionError:
                #     pass
                # except TimeoutError:
                #     pass

            # await artist choice or leaves or timesout

            # start round timer and listen to chat messages

            # append scores as guesses come in

            # rounds need turns...

    except asyncio.CancelledError:
        pass
    finally:
        logger.warning("cleanup database and remove game from room")


async def members_change(app, *, room_uuid, last_known=None):
    if last_known is None:
        last_known = {object()}

    async with app.subscribe('ROOM_UPDATED') as messages:
        async for data in messages:
            if data['uuid'] != room_uuid:
                continue

            room = Room(**data)
            if set(room.members) != set(last_known):
                return room


async def run(app, *, room_uuid):
    logger.info(f"GAME LOOP STARTED {room_uuid}")
    game = None
    membership_changed = asyncio.create_task(
        members_change(app, room_uuid=room_uuid)
    )

    pending = {membership_changed}

    while True:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        [done] = done

        if membership_changed is done:
            room = await done
            membership_changed = asyncio.create_task(
                members_change(app, room_uuid=room_uuid, last_known=room.members)
            )
            pending = {*pending, membership_changed}

            # promote new owner if they've gone
            if room.members and room.owner not in room.members:
                room.owner = random.choice(room.members)
                await update(room, conn=app.redis)

            # user could have multiple browser tabs open
            unique_members = set(room.members)

            game_running = game in pending
            start_game = len(unique_members) >= 2 and not game_running
            suspend_game = len(unique_members) == 1 and game_running
            close_room = len(unique_members) == 0

            if start_game:
                logger.info(f"GAME STARTED {room_uuid}")
                game = asyncio.create_task(host_game(app, room_uuid=room_uuid))
                pending = {*pending, game}
            elif suspend_game:
                logger.info(f"GAME SUSPENDED {room_uuid}")
                pending = pending - {game}
                await cancel_tasks(game)
            elif close_room:
                await cancel_tasks(pending)
                room = await select(Room, room_uuid, conn=app.redis)
                await delete(room, conn=app.redis)
                logger.info(f"ROOM CLOSED {room.uuid}")
                break

        elif game is done:
            logger.info(f"GAME COMPLETE, RESTARTING {room.uuid}")
            game = asyncio.create_task(host_game(app, room_uuid=room_uuid))
            pending = {*pending, game}

    await cancel_tasks(pending)
