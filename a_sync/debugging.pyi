from logging import Logger
from typing import (
    Any,
    AsyncGenerator,
    AsyncIterator,
    Awaitable,
    Callable,
    Literal,
    NoReturn,
    TypeVar,
    overload,
)

from typing_extensions import Concatenate, ParamSpec

from a_sync.a_sync.base import ASyncGenericBase
from a_sync.a_sync.method import ASyncBoundMethod
from a_sync.iter import ASyncGeneratorFunction

__P = ParamSpec("__P")
__T = TypeVar("__T")
__TYield = TypeVar("__TYield")
__TReturn = TypeVar("__TReturn")
__TBase = TypeVar("__TBase", bound=ASyncGenericBase)

_FIVE_MINUTES: Literal[300] = 300

@overload
def stuck_coro_debugger(
    fn: Callable[Concatenate[__TBase, __P], AsyncGenerator[__TYield, Any]],
    logger: Logger = logger,
    interval: int = _FIVE_MINUTES,
) -> ASyncGeneratorFunction[__P, __TYield]: ...
@overload
def stuck_coro_debugger(
    fn: Callable[Concatenate[__TBase, __P], AsyncIterator[__TYield]],
    logger: Logger = logger,
    interval: int = _FIVE_MINUTES,
) -> ASyncGeneratorFunction[__P, __TYield]: ...
@overload
def stuck_coro_debugger(
    fn: Callable[Concatenate[__TBase, __P], Awaitable[__T]],
    logger: Logger = logger,
    interval: int = _FIVE_MINUTES,
) -> ASyncBoundMethod[__TBase, __P, __T]: ...
@overload
def stuck_coro_debugger(
    fn: Callable[Concatenate[__TBase, __P], __T],
    logger: Logger = logger,
    interval: int = _FIVE_MINUTES,
) -> ASyncBoundMethod[__TBase, __P, __T]: ...
@overload
def stuck_coro_debugger(
    fn: Callable[__P, AsyncGenerator[__TYield, __TReturn]],
    logger: Logger = logger,
    interval: int = _FIVE_MINUTES,
) -> Callable[__P, AsyncGenerator[__TYield, __TReturn]]: ...
@overload
def stuck_coro_debugger(
    fn: Callable[__P, AsyncIterator[__TYield]],
    logger: Logger = logger,
    interval: int = _FIVE_MINUTES,
) -> Callable[__P, AsyncIterator[__TYield]]: ...
@overload
def stuck_coro_debugger(
    fn: Callable[__P, Awaitable[__T]], logger: Logger = logger, interval: int = _FIVE_MINUTES
) -> Callable[__P, Awaitable[__T]]: ...
def stuck_coro_debugger(fn, logger=logger, interval=_FIVE_MINUTES): ...
async def _stuck_debug_task(
    logger: Logger, interval: int, fn: Callable[__P, __T], *args: __P.args, **kwargs: __P.kwargs
) -> NoReturn: ...

__all__ = ["stuck_coro_debugger"]
