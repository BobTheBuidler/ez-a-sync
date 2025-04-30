# cython: profile=False
# cython: linetrace=False
import asyncio
import inspect
import functools
import time
from logging import DEBUG, Logger, getLogger
from typing import AsyncIterator, Callable, NoReturn, TypeVar

from typing_extensions import Concatenate, ParamSpec

from a_sync.a_sync.base import ASyncGenericBase
from a_sync.iter cimport _ASyncGeneratorFunction


__P = ParamSpec("__P")
__T = TypeVar("__T")
__B = TypeVar("__B", bound=ASyncGenericBase)


cdef object _FIVE_MINUTES = 300

cdef object create_task = asyncio.create_task
cdef object sleep = asyncio.sleep

cdef object isasyncgenfunction = inspect.isasyncgenfunction

cdef object wraps = functools.wraps

cdef object gettime = time.time

cdef object logger = getLogger("a_sync.debugging")


def stuck_coro_debugger(fn, logger=logger, interval=_FIVE_MINUTES):
    __logger_is_enabled_for = logger.isEnabledFor

    if isasyncgenfunction(fn) or isinstance(fn, _ASyncGeneratorFunction):

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

    start = gettime() - interval
    cdef str module = fn.__module__
    cdef str name = fn.__name__
    cdef tuple formatted_args = tuple(map(str, args))
    cdef dict formatted_kwargs = dict(zip(kwargs.keys(), map(str, kwargs.values())))
    log = logger._log
    while True:
        log(
            DEBUG,
            "%s.%s still executing after %sm with args %s kwargs %s",
            (
                module,
                name,
                round((gettime() - start) / 60, 2),
                formatted_args,
                formatted_kwargs,
            ),
        )
        await sleep(interval)


__all__ = ["stuck_coro_debugger"]
