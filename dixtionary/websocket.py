import asyncio
import json
import traceback

from typing import NamedTuple

from aiostream import stream
from sanic.websocket import ConnectionClosed
from sanic.exceptions import InvalidUsage, SanicException, ServerError

from dixtionary.utils.asynchronous import yield_with, keep_awaiting

CLIENT_MESSAGE = object()


class ContainedException(NamedTuple):
    exc: Exception


async def contain_exceptions(gen):
    try:
        async for value in gen:
            yield value
    except Exception as e:
        yield ContainedException(exc=e)


async def websocket_handler(request, ws):
    """
    Handles lifecycle of a connected websocket client.

    This function is called per client connection and then
    stays open indefinitely unless the client closes it.
    """
    task_queue = asyncio.Queue()

    async def put(*, key, task):
        # All tasks should yield any values with
        # themselves so the original request can be looked up
        keyed_task = yield_with(key, gen=task)
        await task_queue.put(keyed_task)

    await put(key=CLIENT_MESSAGE, task=keep_awaiting(ws.recv))

    async with stream.flatten(keep_awaiting(task_queue.get)).stream() as streamer:
        async for request_key, result in streamer:

            if request_key is CLIENT_MESSAGE and isinstance(result, ContainedException):
                try:
                    raise ContainedException.exc
                except ConnectionClosed:
                    # Client disconnects
                    # TODO: appropriate cleanup of pending tasks
                    raise

            elif request_key is CLIENT_MESSAGE:
                try:
                    task_request = Task.from_message(result, base_request=request)
                except SanicException as e:
                    if request.app.config.TE_DEBUG:
                        traceback.print_exc()
                    response = Response(uuid=None, error=e)
                    await ws.send(json.dumps(response.asdict()))
                except ValueError:
                    if request.app.config.TE_DEBUG:
                        traceback.print_exc()
                    # problem parsing client message
                    response = Response(
                        uuid=None,
                        error=InvalidUsage(f'Error parsing message: "{result}".')
                    )
                    await ws.send(json.dumps(response.asdict()))
                else:
                    # Exceptions should be caught to keep websocket alive when task errors
                    subdued_task = contain_exceptions(task_request.run())
                    # Add to task queue
                    await put(key=task_request, task=subdued_task)

            elif isinstance(request_key, Task) and isinstance(result, ContainedException):
                task_request = request_key
                # noinspection PyBroadException
                try:
                    raise result.exc
                except SanicException as e:
                    if request.app.config.TE_DEBUG:
                        traceback.print_exc()
                    response = Response(uuid=task_request.uuid, error=e)
                    await ws.send(json.dumps(response.asdict()))
                except Exception:
                    traceback.print_exc()
                    # TODO: log and report underlying exception
                    response = Response(uuid=task_request.uuid, error=ServerError())
                    await ws.send(json.dumps(response.asdict()))

            elif isinstance(request_key, Task):
                task_request = request_key
                # return task result to client
                response = Response(uuid=task_request.uuid, result=result)
                await ws.send(json.dumps(response.asdict()))

            else:
                # Should never be hit.
                # Tasks added to the queue should only ever be new messages from the
                # client or completing tasks in the form of a Request.
                raise ValueError('Unknown request type returned', request_key)
