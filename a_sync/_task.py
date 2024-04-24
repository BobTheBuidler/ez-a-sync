
import asyncio
import logging

from a_sync import exceptions
from a_sync._typing import *


logger = logging.getLogger(__name__)

def create_task(
    coro: Awaitable[T], 
    *, 
    name: Optional[str] = None, 
    skip_gc_until_done: bool = False,
    log_destroyed_pending: bool = True,
) -> "asyncio.Task[T]":
    """
    Extends asyncio.create_task to support any Awaitable, manage task lifecycle, and enhance error handling.

    Unlike asyncio.create_task, which requires a coroutine, this function accepts any Awaitable, ensuring broader
    compatibility. It optionally prevents the task from being garbage-collected until completion and provides
    enhanced error management by wrapping exceptions in a custom exception.

    Args:
        coro: An Awaitable object from which to create the task.
        name: Optional name for the task, aiding in debugging.
        skip_gc_until_done: If True, the task is kept alive until it completes, preventing garbage collection.
        log_destroyed_pending: If False, asyncio's default error log when a pending task is destroyed is suppressed.

    Returns:
        An asyncio.Task object created from the provided Awaitable.
    """

    if not asyncio.iscoroutine(coro):
        coro = __await(coro)
    task = asyncio.create_task(coro, name=name)
    if skip_gc_until_done:
        __persist(asyncio.create_task(__persisted_task_exc_wrap(task)))
    if not log_destroyed_pending:
        task._log_destroyed_pending = False
    return task


__persisted_tasks: Set["asyncio.Task[Any]"] = set()

async def __await(awaitable: Awaitable[T]) -> T:
    """Wait for the completion of an Awaitable."""
    try:
        return await awaitable
    except RuntimeError as e:
        args = [e, awaitable]
        if isinstance(awaitable, asyncio.tasks._GatheringFuture):
            args.append(awaitable._children)
        raise RuntimeError(*args) from None

    
def __persist(task: "asyncio.Task[Any]") -> None:
    """Add a task to the set of persisted tasks."""
    __persisted_tasks.add(task)
    __prune_persisted_tasks()

def __prune_persisted_tasks():
    """Remove completed tasks from the set of persisted tasks."""
    for task in tuple(__persisted_tasks):
        if task.done():
            if (e := task.exception()) and not isinstance(e, exceptions.PersistedTaskException):
                logger.exception(e)
                raise e
            __persisted_tasks.discard(task)

async def __persisted_task_exc_wrap(task: "asyncio.Task[T]") -> T:
    """
    Wrap a task to handle its exception in a specialized manner.

    Args:
        task: The asyncio Task to wrap.

    Returns:
        The result of the task, if successful.

    Raises:
        PersistedTaskException: Wraps any exception raised by the task for special handling.
    """
    try:
        return await task
    except Exception as e:
        raise exceptions.PersistedTaskException(e, task) from e