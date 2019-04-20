import random
import asyncio

from uuid import uuid4

from loguru import logger

from dixtionary.model.query import Room, Game, Round, Turn, Score, Message
from dixtionary.database import select, insert, update, delete
from dixtionary.utils.asynchronous import cancel_tasks


with open('dixtionary/gameplay/dictionary.txt', 'r') as fp:
    DICTIONARY = fp.read().splitlines()


async def countdown(app, *, seconds, turn_uuid):
    turn = await select(Turn, turn_uuid, conn=app.redis)
    turn.remaining = seconds
    await update(turn, conn=app.redis)

    while True:
        await asyncio.sleep(1)
        turn = await select(Turn, turn_uuid, conn=app.redis)
        turn.remaining -= 1
        await update(turn, conn=app.redis)

        if turn.remaining == 0:
            break


async def artist_choice(app, *, turn_uuid):
    turn = await select(Turn, turn_uuid, conn=app.redis)

    if turn.choice:
        return turn.choice

    async with app.subscribe('TURN_UPDATED') as messages:
        async for data in messages:
            turn = Turn(**data)

            if turn.uuid == turn_uuid and turn.choice:
                return turn.choice


async def cycle_turns(app, *, room_uuid, round_uuid):
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
            complete=False,
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

            turns = cycle_turns(app, room_uuid=room.uuid, round_uuid=round_.uuid)

            async for turn in turns:
                logger.info(f"TURN {turn.artist} {room_uuid}")
                round_.turns.append(turn)
                await insert(turn, conn=app.redis)
                await update(round_, conn=app.redis)

                await asyncio.sleep(10)

                timeout = asyncio.create_task(
                    countdown(app, seconds=10, turn_uuid=turn.uuid)
                )
                choice = asyncio.create_task(
                    artist_choice(app, turn_uuid=turn.uuid)
                )
                artist_leaves = asyncio.create_task(
                    member_leaves(app, room_uuid=room_uuid, member_uuid=turn.artist)
                )

                done, pending = await asyncio.wait(
                    {choice, timeout, artist_leaves},
                    return_when=asyncio.FIRST_COMPLETED
                )
                [done] = done

                if done in {timeout, artist_leaves}:
                    continue

                choice = await choice

                # start round timer and listen to chat messages

                # append scores as guesses come in

        # let the winners bask in their glory
        game = await select(Game, game.uuid, conn=app.redis)
        game.complete = True
        await update(game, conn=app.redis)
        await asyncio.sleep(10)
    finally:
        game = await select(Game, game.uuid, conn=app.redis)
        rounds = [await select(Round, r, conn=app.redis) for r in game.rounds]
        turns = [await select(Turn, t, conn=app.redis) for r in rounds for t in r.turns]
        scores = [await select(Score, s, conn=app.redis) for t in turns for s in t.scores]

        for entity in [game, *rounds, *turns, *scores]:
            await delete(entity, conn=app.redis)


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


async def member_leaves(app, *, room_uuid, member_uuid):
    room = await select(Room, room_uuid, conn=app.redis)
    if member_uuid not in room.members:
        return True

    async for room in members_change(app, room_uuid=room_uuid):
        if member_uuid not in room.members:
            return True


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

            # re-register for next change
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
                messages = [select(Message, m, conn=app.redis) for m in room.chat]

                for entity in [room, *messages]:
                    await delete(entity, conn=app.redis)

                logger.info(f"ROOM CLOSED {room.uuid}")
                break

        elif game is done:
            logger.info(f"GAME COMPLETE, RESTARTING {room.uuid}")
            game = asyncio.create_task(host_game(app, room_uuid=room_uuid))
            pending = {*pending, game}

    await cancel_tasks(pending)
