from asyncio import create_task, sleep
from inspect import isasyncgenfunction
from logging import DEBUG, Logger, getLogger
from functools import wraps
from time import time
from typing import AsyncIterator, Awaitable, Callable, NoReturn, TypeVar, overload

from typing_extensions import Concatenate, ParamSpec

from a_sync.a_sync.base import ASyncGenericBase
from a_sync.a_sync.method import ASyncBoundMethod
from a_sync.iter import ASyncGeneratorFunction


__P = ParamSpec("__P")
__T = TypeVar("__T")
__B = TypeVar("__B", bound=ASyncGenericBase)


_FIVE_MINUTES = 300

logger = getLogger("a_sync.debugging")


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


def stuck_coro_debugger(fn, logger=logger, interval=_FIVE_MINUTES):
    __logger_is_enabled_for = logger.isEnabledFor

    if isasyncgenfunction(fn):

        @wraps(fn)
        async def stuck_async_gen_wrap(*args: __P.args, **kwargs: __P.kwargs) -> AsyncIterator[__T]:
            aiterator = fn(*args, **kwargs)

            if not __logger_is_enabled_for(DEBUG):
                async for thing in aiterator:
                    yield thing
                return

            task = create_task(
                coro=_stuck_debug_task(logger, interval, fn, args, kwargs),
                name="_stuck_debug_task",
            )
            try:
                async for thing in aiterator:
                    yield thing
            finally:
                task.cancel()

        return stuck_async_gen_wrap
    else:

        @wraps(fn)
        async def stuck_coro_wrap(*args: __P.args, **kwargs: __P.kwargs) -> __T:
            if not __logger_is_enabled_for(DEBUG):
                return await fn(*args, **kwargs)

            task = create_task(
                coro=_stuck_debug_task(logger, interval, fn, args, kwargs),
                name="_stuck_debug_task",
            )
            try:
                retval = await fn(*args, **kwargs)
            finally:
                task.cancel()
            return retval

        return stuck_coro_wrap


async def _stuck_debug_task(
    logger: Logger, interval: int, fn: Callable[__P, __T], *args: __P.args, **kwargs: __P.kwargs
) -> NoReturn:
    # sleep early so fast-running coros can exit early
    await sleep(interval)

    start = time() - interval
    module = fn.__module__
    name = fn.__name__
    formatted_args = tuple(map(str, args))
    formatted_kwargs = dict(zip(kwargs.keys(), map(str, kwargs.values())))
    log = logger._log
    while True:
        log(
            DEBUG,
            "%s.%s still executing after %sm with args %s kwargs %s",
            (
                module,
                name,
                round((time() - start) / 60, 2),
                formatted_args,
                formatted_kwargs,
            ),
        )
        await sleep(interval)


__all__ = ["stuck_coro_debugger"]
