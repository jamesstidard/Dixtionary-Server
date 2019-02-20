
async def keep_awaiting(awaitable):
    while True:
        yield await awaitable()


async def yield_with(*args, gen):
    async for value in gen:
        yield tuple([*args, value])
