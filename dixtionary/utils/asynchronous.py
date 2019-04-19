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
