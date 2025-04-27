from logging import Logger
from typing import AsyncIterator, Awaitable, Callable, Literal, NoReturn, TypeVar, overload

from typing_extensions import Concatenate, ParamSpec

from a_sync.a_sync.base import ASyncGenericBase
from a_sync.a_sync.method import ASyncBoundMethod
from a_sync.iter import ASyncGeneratorFunction


__P = ParamSpec("__P")
__T = TypeVar("__T")
__B = TypeVar("__B", bound=ASyncGenericBase)


_FIVE_MINUTES: Literal[300] = 300


@overload
def stuck_coro_debugger(
    fn: Callable[Concatenate[__B, __P], AsyncIterator[__T]],
    logger: Logger = logger,
    interval: int = _FIVE_MINUTES,
) -> ASyncGeneratorFunction[__P, __T]: ...


@overload
def stuck_coro_debugger(
    fn: Callable[Concatenate[__B, __P], Awaitable[__T]],
    logger: Logger = logger,
    interval: int = _FIVE_MINUTES,
) -> ASyncBoundMethod[__B, __P, __T]: ...


@overload
def stuck_coro_debugger(
    fn: Callable[Concatenate[__B, __P], __T], logger: Logger = logger, interval: int = _FIVE_MINUTES
) -> ASyncBoundMethod[__B, __P, __T]: ...


@overload
def stuck_coro_debugger(
    fn: Callable[__P, AsyncIterator[__T]], logger: Logger = logger, interval: int = _FIVE_MINUTES
) -> Callable[__P, AsyncIterator[__T]]: ...


@overload
def stuck_coro_debugger(
    fn: Callable[__P, Awaitable[__T]], logger: Logger = logger, interval: int = _FIVE_MINUTES
) -> Callable[__P, Awaitable[__T]]: ...


def stuck_coro_debugger(fn, logger=logger, interval=_FIVE_MINUTES): ...


async def _stuck_debug_task(
    logger: Logger, interval: int, fn: Callable[__P, __T], *args: __P.args, **kwargs: __P.kwargs
) -> NoReturn: ...


__all__ = ["stuck_coro_debugger"]
