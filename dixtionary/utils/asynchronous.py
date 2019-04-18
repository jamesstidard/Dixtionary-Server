import asyncio

from typing import Iterable


async def cancel_tasks(tasks):
    if not isinstance(tasks, Iterable):
        tasks = [tasks]

    tasks = asyncio.gather(*tasks)
    tasks.cancel()

    try:
        await tasks
    except asyncio.CancelledError:
        pass
