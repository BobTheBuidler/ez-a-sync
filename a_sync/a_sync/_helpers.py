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
        awaitable (Awaitable[T]): The awaitable object to be awaited.

    Raises:
        exceptions.SyncModeInAsyncContextError: If the event loop is already running.

    Examples:
        >>> async def example_coroutine():
        ...     return 42
        ...
        >>> result = _await(example_coroutine())
        >>> print(result)
        42

    See Also:
        - :func:`asyncio.run`: For running the main entry point of an asyncio program.
    """
    try:
        return a_sync.asyncio.get_event_loop().run_until_complete(awaitable)
    except RuntimeError as e:
        if str(e) == "This event loop is already running":
            raise exceptions.SyncModeInAsyncContextError from None
        raise


def _asyncify(func: SyncFn[P, T], executor: Executor) -> CoroFn[P, T]:  # type: ignore [misc]
    """
    Convert a synchronous function to a coroutine function using an executor.

    This function submits the synchronous function to the provided executor and wraps
    the resulting future in a coroutine function. This allows the synchronous function
    to be executed asynchronously.

    Note:
        The function `_asyncify` uses `asyncio.futures.wrap_future` to wrap the future
        returned by the executor, specifying the event loop with `a_sync.asyncio.get_event_loop()`.
        Ensure that your environment supports this usage or adjust the import if necessary.

    Args:
        func (SyncFn[P, T]): The synchronous function to be converted.
        executor (Executor): The executor used to run the synchronous function.

    Raises:
        exceptions.FunctionNotSync: If the input function is a coroutine function or an instance of :class:`~a_sync.a_sync.function.ASyncFunction`.

    Examples:
        >>> from concurrent.futures import ThreadPoolExecutor
        >>> def sync_function(x):
        ...     return x * 2
        ...
        >>> executor = ThreadPoolExecutor()
        >>> async_function = _asyncify(sync_function, executor)
        >>> result = await async_function(3)
        >>> print(result)
        6

    See Also:
        - :class:`concurrent.futures.Executor`: For managing pools of threads or processes.
        - :func:`asyncio.to_thread`: For running blocking code in a separate thread.
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
