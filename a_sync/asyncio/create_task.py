"""
This module extends asyncio.create_task to support any Awaitable,
manage task lifecycle, and enhance error handling.
"""

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
    log_destroy_pending: bool = True,
) -> "asyncio.Task[T]":
    """
    Extends asyncio.create_task to support any Awaitable, manage task lifecycle, and enhance error handling.

    This function accepts any Awaitable, ensuring broader compatibility. If the Awaitable is not a coroutine,
    it attempts to convert it to one. It optionally prevents the task from being garbage-collected until completion
    and provides enhanced error management by wrapping exceptions in a custom exception when skip_gc_until_done is True.

    Args:
        coro: An Awaitable object from which to create the task. If not a coroutine, it will be converted.
        name: Optional name for the task, aiding in debugging.
        skip_gc_until_done: If True, the task is kept alive until it completes, preventing garbage collection.
                            Exceptions are wrapped in PersistedTaskException for special handling.
        log_destroy_pending: If False, asyncio's default error log when a pending task is destroyed is suppressed.

    Returns:
        An asyncio.Task object created from the provided Awaitable.
    """

    if not asyncio.iscoroutine(coro):
        coro = __await(coro)
    task = asyncio.create_task(coro, name=name)
    if skip_gc_until_done:
        __persisted_tasks.add(asyncio.create_task(__persisted_task_exc_wrap(task)))
    if log_destroy_pending is False:
        asyncio.Task.__del__
        task._log_destroy_pending = False
    __prune_persisted_tasks()
    return task


__persisted_tasks: Set["asyncio.Task[Any]"] = set()


async def __await(awaitable: Awaitable[T]) -> T:
    """Wait for the completion of an Awaitable.

    Args:
        awaitable: The Awaitable object to wait for.

    Raises:
        RuntimeError: If a RuntimeError occurs during the await, it is raised with additional context.
    """
    try:
        return await awaitable
    except RuntimeError as e:
        args = [e, awaitable]
        if isinstance(awaitable, asyncio.tasks._GatheringFuture):
            args.append(awaitable._children)
        raise RuntimeError(*args) from None


def __prune_persisted_tasks():
    """Remove completed tasks from the set of persisted tasks.

    This function checks each task in the persisted tasks set. If a task is done and has an exception,
    it logs the exception and raises it if it's not a PersistedTaskException. It also logs the traceback
    manually since the usual handler will not run after retrieving the exception.
    """
    for task in tuple(__persisted_tasks):
        if task.done() and (e := task.exception()):
            # force exceptions related to this lib to bubble up
            if not isinstance(e, exceptions.PersistedTaskException):
                logger.exception(e)
                raise e
            # we have to manually log the traceback that asyncio would usually log
            # since we already got the exception from the task and the usual handler will now not run
            context = {
                "message": f"{task.__class__.__name__} exception was never retrieved",
                "exception": e,
                "future": task,
            }
            if task._source_traceback:
                context["source_traceback"] = task._source_traceback
            task._loop.call_exception_handler(context)
            __persisted_tasks.discard(task)


async def __persisted_task_exc_wrap(task: "asyncio.Task[T]") -> T:
    """
    Wrap a task to handle its exception in a specialized manner.

    Args:
        task: The asyncio Task to wrap.

    Raises:
        PersistedTaskException: Wraps any exception raised by the task for special handling.
    """
    try:
        return await task
    except Exception as e:
        raise exceptions.PersistedTaskException(e, task) from e


__all__ = ["create_task"]
