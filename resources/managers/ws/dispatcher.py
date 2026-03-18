import typing as t
from dataclasses import dataclass


@dataclass
class WSDispatcher:

    def __post_init__(self):
        self._handlers: t.Dict[str, t.Callable] = {}

    def handler(self, command: str):
        def decorator(func):
            self._handlers[command] = func
            return func

        return decorator

    def get_handlers(self) -> t.Dict[str, t.Callable]:
        return self._handlers
