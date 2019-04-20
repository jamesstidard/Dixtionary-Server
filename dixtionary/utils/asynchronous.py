import asyncio


async def cancel_tasks(tasks):
    if asyncio.isfuture(tasks):
        tasks = [tasks]

    tasks = asyncio.gather(*tasks)
    tasks.cancel()

    try:
        await tasks
    except asyncio.CancelledError:
        pass


async def first_completed(tasks):
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    return done[0], pending
