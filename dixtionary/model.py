import json
from inspect import isawaitable, isasyncgen
from typing import Optional, NamedTuple, Any

from sanic.request import Request as SanicRequest
from sanic.exceptions import InvalidUsage, SanicException


class Request(NamedTuple):
    uuid: Optional[str]
    action: str
    kwargs: dict
    base_request: SanicRequest

    @staticmethod
    def from_request(request, *, action):
        kwargs = {str(k): json.loads(v) for k, v in request.raw_args.items()}
        return Request(uuid=None, action=action, kwargs=kwargs, base_request=request)

    @staticmethod
    def from_message(message, *, base_request: SanicRequest):
        kwargs = json.loads(message)
        kwargs['base_request'] = base_request
        return Request(**kwargs)

    @property
    def app(self):
        return self.base_request.app

    async def run(self):
        try:
            action = self.action.lower()
        except KeyError:
            raise InvalidUsage(dev_message=f'Unknown action: "{self.action}"')

        if hasattr(action, '__pass_request__'):
            result = action(self, **self.kwargs)
        else:
            result = action(**self.kwargs)

        if isawaitable(result):
            yield await result
        elif isasyncgen(result):
            async for r in result:
                yield r
        else:
            yield result


class Response(NamedTuple):
    uuid: Optional[str]
    result: Any = None
    error: SanicException = None

    def asdict(self):
        result = {
            'uuid': self.uuid,
            'result': self.result,
            'error': None,
        }
        if self.error:
            result['error'] = {
                'status_code': self.error.status_code,
                'args': ', '.join(self.error.args),
            }
        return result
