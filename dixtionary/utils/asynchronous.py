import asyncio

from loguru import logger

from aiostream import streamcontext
from aiostream.aiter_utils import anext
from aiostream.core import Stream, Streamer


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
    return list(done)[0], pending


class HotAsyncIterator:

    def __init__(self, queue):
        self.queue = queue

    def __aiter__(self):
        return self

    async def __anext__(self):
        next_ = await self.queue.get()
        value = await asyncio.shield(next_)
        return value


class HotStreamer(Streamer):

    def __init__(self, source, maxlen=1):
        self.source = source
        self.maxlen = maxlen

        self.queues = []
        self.task = None
        self.future = None
        self.started = asyncio.Event()

    async def __aenter__(self):
        self.task = asyncio.create_task(self._target())
        await self.started.wait()
        return self

    async def __aexit__(self, *args):
        await self.aclose()

    async def _target(self):
        async with streamcontext(self.source) as streamer:
            while True:
                try:
                    coro = anext(streamer)
                    self.future = asyncio.create_task(coro)
                    for queue in self.queues:
                        if queue.full():
                            _ = queue.get_nowait()
                        queue.put_nowait(self.future)
                    self.started.set()
                    await self.future
                except Exception:
                    break
                finally:
                    await cancel_tasks(self.future)

    def __aiter__(self):
        queue = asyncio.Queue(maxsize=self.maxlen)
        queue.put_nowait(self.future)
        self.queues.append(queue)
        return HotAsyncIterator(queue)

    async def aclose(self):
        await cancel_tasks(self.task)


class HotStream(Stream):

    def __init__(self, source, maxlen=1):
        self.source = source
        self.maxlen = maxlen

    def __aiter__(self):
        return HotStreamer(self.source, self.maxlen)


def hotstream(*args, **kwargs):
    return HotStream(*args, **kwargs)
