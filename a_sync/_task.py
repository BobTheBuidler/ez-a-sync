
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
        __persisted_tasks.add(asyncio.create_task(__persisted_task_exc_wrap(task)))
    if log_destroy_pending is False:
        task._log_destroy_pending = False
    __prune_persisted_tasks()
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

def __prune_persisted_tasks():
    """Remove completed tasks from the set of persisted tasks."""
    for task in tuple(__persisted_tasks):
        if task.done() and (e := task.exception()):
            # force exceptions related to this lib to bubble up
            if not isinstance(e, exceptions.PersistedTaskException):
                logger.exception(e)
                raise e
            # we have to manually log the traceback that asyncio would usually log 
            # since we already got the exception from the task and the usual handler will now not run
            context = {
                'message': f'{task.__class__.__name__} exception was never retrieved',
                'exception': e,
                'future': task,
            }
            if task._source_traceback:
                context['source_traceback'] = task._source_traceback
            task._loop.call_exception_handler(context)
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