import asyncio
import typing


class EventCallback:
    def __init__(self, event: str, func: callable):
        self.func = func
        self.event = event


T = typing.TypeVar('T')


async def _dispatch_event(self, name, payload):
    callback = self._callbacks.get(name)
    if not callback:
        callback = self._callbacks.get("unhandled_event")

    if callback:
        return asyncio.create_task(callback(self, payload))


def _get_event_callback(self, name):
    callback = self._callbacks.get(name)
    if not callback:
        callback = self._callbacks.get("unhandled_event")

    return callback.__get__(self)


class EventDispatchType(typing.Protocol):
    async def _dispatch_event(self, name: str, payload: dict) -> typing.Optional[asyncio.Task]: ...

    def _get_event_callback(self, name: str) -> typing.Optional[callable]: ...


def event_dispatch(cls: type[T]) -> type[T]:
    """
    Allow definition of event handlers using the `register_callback()` wrapper. Any unhandled events will be sent
    to the "unhandled_event" handler.
    """

    cls._callbacks = {}
    processed = set()

    def find_callbacks(root):
        for base in reversed(root.__mro__):
            if base in processed:
                continue
            else:
                processed.add(base)

            find_callbacks(base)
            if hasattr(base, '_callbacks'):
                cls._callbacks.update(base._callbacks)

    find_callbacks(cls)

    for key, value in cls.__dict__.items():
        if isinstance(value, EventCallback):
            cls._callbacks[value.event] = value.func
            setattr(cls, key, value.func)

    cls._dispatch_event = _dispatch_event
    cls._get_event_callback = _get_event_callback

    return cls


def register_callback(event: str):
    def inner(callback: callable):
        return EventCallback(event, callback)

    return inner
