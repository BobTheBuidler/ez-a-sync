"""
This module extends :func:`asyncio.create_task` to support any :class:`Awaitable`,
manage task lifecycle, and enhance error handling.
"""

import asyncio.tasks as aiotasks
from asyncio import Future, InvalidStateError, Task, get_running_loop, iscoroutine
from logging import getLogger

from a_sync._smart import SmartTask, smart_task_factory
from a_sync._typing import *
from a_sync.exceptions import PersistedTaskException


cdef public object logger = getLogger(__name__)


def create_task(
    coro: Awaitable[T],
    *,
    name: str = "",
    skip_gc_until_done: bint = False,
    log_destroy_pending: bint = True,
) -> "Task[T]":
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
        log_destroy_pending: If False, asyncio's default error log when a pending task is destroyed is suppressed.

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
        - :class:`Task`
    """
    return ccreate_task(coro, name, skip_gc_until_done, log_destroy_pending)

cdef object ccreate_task_simple(object coro):
    return ccreate_task(coro, "", False, True)
    
cdef object ccreate_task(object coro, str name, bint skip_gc_until_done, bint log_destroy_pending):
    cdef object loop = get_running_loop()
    cdef object task_factory = loop._task_factory
    cdef object task, persisted
    
    if not iscoroutine(coro):
        coro = __await(coro)
    
    if task_factory is None:
        task = Task(coro, loop=loop, name=name)
        if task._source_traceback:
            del task._source_traceback[-1]
    elif task_factory is smart_task_factory:
        task = SmartTask(coro, loop=loop, name=name)
        if task._source_traceback:
            del task._source_traceback[-1]
    else:
        task = task_factory(loop, coro)
        if name:
            __set_task_name(task, name)

    if skip_gc_until_done:
        persisted = __persisted_task_exc_wrap(task)
            
        if task_factory is None:
            persisted = Task(persisted, loop=loop, name=name)
            if persisted._source_traceback:
                del persisted._source_traceback[-1]
        elif task_factory is smart_task_factory:
            persisted = SmartTask(persisted, loop=loop, name=name)
            if persisted._source_traceback:
                del persisted._source_traceback[-1]
        else:
            persisted = task_factory(loop, persisted)
            if name:
                __set_task_name(persisted, name)
            
        __persisted_tasks.add(persisted)

    if log_destroy_pending is False:
        task._log_destroy_pending = False

    __prune_persisted_tasks()

    return task


cdef inline void __set_task_name(object task, str name):
    if set_name := getattr(task, "set_name", None):
         set_name(name)


__persisted_tasks: Set["Task[Any]"] = set()


async def __await(awaitable: Awaitable[T]) -> T:
    """Wait for the completion of a non-coroutine Awaitable.

    Args:
        awaitable: The :class:`Awaitable` object to wait for.

    Raises:
        RuntimeError: If a RuntimeError occurs during the await, it is raised with additional context.

    Examples:
        Await a simple coroutine:

        >>> async def my_coroutine():
        ...     return "Hello, World!"
        >>> result = await __await(my_coroutine())

    See Also:
        - :class:`Awaitable`
    """
    try:
        return await awaitable
    except RuntimeError as e:
        args = [e, awaitable]
        if isinstance(awaitable, aiotasks._GatheringFuture):
            args.append(awaitable._children)
        raise RuntimeError(*args) from None

   
cdef object __log_exception = logger.exception


cdef void __prune_persisted_tasks():
    """Remove completed tasks from the set of persisted tasks.

    This function checks each task in the persisted tasks set. If a task is done and has an exception,
    it logs the exception and raises it if it's not a :class:`PersistedTaskException`. It also logs the traceback
    manually since the usual handler will not run after retrieving the exception.

    See Also:
        - :class:`PersistedTaskException`
    """
    cdef object task
    cdef dict context
    for task in tuple(__persisted_tasks):
        if _is_done(task):
            if e := _get_exception(task):
                # force exceptions related to this lib to bubble up
                if not isinstance(e, PersistedTaskException):
                    __log_exception(e)
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


cdef inline bint _is_done(fut: Future):
    return <str>fut._state != "PENDING"


cdef object _get_exception(fut: Future):
    """Return the exception that was set on this future.

    The exception (or None if no exception was set) is returned only if
    the future is done.  If the future has been cancelled, raises
    CancelledError.  If the future isn't done yet, raises
    InvalidStateError.
    """
    cdef str state = fut._state
    if state == "FINISHED":
        fut._Future__log_traceback = False
        return fut._exception
    if state == "CANCELLED":
        raise fut._make_cancelled_error()
    raise InvalidStateError('Exception is not set.')


async def __persisted_task_exc_wrap(task: "Task[T]") -> T:
    """
    Wrap a task to handle its exception in a specialized manner.

    Args:
        task: The :class:`Task` to wrap.

    Raises:
        PersistedTaskException: Wraps any exception raised by the task for special handling.

    See Also:
        - :class:`PersistedTaskException`
    """
    try:
        return await task
    except Exception as e:
        raise PersistedTaskException(e, task) from e


__all__ = ["create_task"]
