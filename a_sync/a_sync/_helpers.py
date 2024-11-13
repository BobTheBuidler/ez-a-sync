"""
This module provides utility functions for handling asynchronous operations
and converting synchronous functions to asynchronous ones.
"""

import asyncio
import functools
from concurrent.futures import Executor

import a_sync.asyncio
from a_sync import exceptions
from a_sync._typing import *


def _await(awaitable: Awaitable[T]) -> T:
    """
    Await an awaitable object in a synchronous context.

    Args:
        awaitable: The awaitable object to be awaited.

    Raises:
        exceptions.SyncModeInAsyncContextError: If the event loop is already running.
    """
    try:
        return a_sync.asyncio.get_event_loop().run_until_complete(awaitable)
    except RuntimeError as e:
        if str(e) == "This event loop is already running":
            raise exceptions.SyncModeInAsyncContextError from None
        raise


def _asyncify(func: SyncFn[P, T], executor: Executor) -> CoroFn[P, T]:  # type: ignore [misc]
    """
    Convert a synchronous function to a coroutine function.

    Args:
        func: The synchronous function to be converted.
        executor: The executor used to run the synchronous function.

    Returns:
        A coroutine function wrapping the input function.

    Raises:
        exceptions.FunctionNotSync: If the input function is a coroutine function or an instance of ASyncFunction.
    """
    from a_sync.a_sync.function import ASyncFunction

    if asyncio.iscoroutinefunction(func) or isinstance(func, ASyncFunction):
        raise exceptions.FunctionNotSync(func)

    @functools.wraps(func)
    async def _asyncify_wrap(*args: P.args, **kwargs: P.kwargs) -> T:
        return await asyncio.futures.wrap_future(
            executor.submit(func, *args, **kwargs),
            loop=a_sync.asyncio.get_event_loop(),
        )

    return _asyncify_wrap
