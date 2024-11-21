"""
This module extends :func:`asyncio.create_task` to support any :class:`Awaitable`,
manage task lifecycle, and enhance error handling.
"""

from a_sync._typing import *
import asyncio

__all__ = ["create_task"]

def create_task(
    coro: Awaitable[T],
    *,
    name: Optional[str] = None,
    skip_gc_until_done: bool = False,
    log_destroy_pending: bool = True
) -> asyncio.Task[T]:
    """
    Extends :func:`asyncio.create_task` to support any :class:`Awaitable`, manage task lifecycle, and enhance error handling.

    This function accepts any :class:`Awaitable`, ensuring broader compatibility. If the Awaitable is not a coroutine,
    it is awaited directly using a private helper function `__await`, which can handle non-coroutine Awaitable objects.

    Note:
        The `__await` function is designed to handle non-coroutine Awaitables by awaiting them directly.

    Args:
        coro: An :class:`Awaitable` object from which to create the task.
        name: Optional name for the task, aiding in debugging.
        skip_gc_until_done: If True, the task is kept alive until it completes, preventing garbage collection.
            Exceptions are wrapped in :class:`PersistedTaskException` for special handling within the
            `__persisted_task_exc_wrap` function.
        log_destroy_pending: If False, asyncio\'s default error log when a pending task is destroyed is suppressed.

    Examples:
        Create a simple task with a coroutine:

        >>> async def my_coroutine():
        ...     return "Hello, World!"
        >>> task = create_task(my_coroutine())

        Create a task with a non-coroutine Awaitable:

        >>> from concurrent.futures import Future
        >>> future = Future()
        >>> task = create_task(future)

    See Also:
        - :func:`asyncio.create_task`
        - :class:`asyncio.Task`
    """
