"""
This module provides utility functions for handling asynchronous operations
and converting synchronous functions to asynchronous ones.
"""

import asyncio
import asyncio.futures as aiofutures
from concurrent.futures import Executor

cimport cython

from a_sync import exceptions
from a_sync._typing import P, T
from a_sync.a_sync.function cimport _ASyncFunction
from a_sync.executor import _AsyncExecutorMixin
from a_sync.functools cimport wraps


# cdef asyncio
cdef object iscoroutinefunction = asyncio.iscoroutinefunction
cdef object get_running_loop = asyncio.get_running_loop
cdef object new_event_loop = asyncio.new_event_loop
cdef object set_event_loop = asyncio.set_event_loop
cdef object _chain_future = aiofutures._chain_future
cdef object _get_event_loop = asyncio.get_event_loop
del asyncio, aiofutures


# cdef exceptions
cdef object FunctionNotSync = exceptions.FunctionNotSync
cdef object SyncModeInAsyncContextError = exceptions.SyncModeInAsyncContextError
del exceptions


@cython.profile(False)
@cython.linetrace(False)
cpdef inline object get_event_loop():
    cdef object loop
    try:
        return _get_event_loop()
    except RuntimeError as e:  # Necessary for use with multi-threaded applications.
        if not str(e).startswith("There is no current event loop in thread"):
            raise
        loop = new_event_loop()
        set_event_loop(loop)
    return loop


@cython.profile(False)
@cython.linetrace(False)
cdef object _await(object awaitable):
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
        return get_event_loop().run_until_complete(awaitable)
    except RuntimeError as e:
        if str(e) == "This event loop is already running":
            raise SyncModeInAsyncContextError from None
        raise


cdef object _asyncify(object func, executor: Executor):  # type: ignore [misc]
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
    if iscoroutinefunction(func) or isinstance(func, _ASyncFunction):
        raise FunctionNotSync(func)
    
    if isinstance(executor, _AsyncExecutorMixin):
        # ASyncExecutor classes are better optimized.
        # TODO: implement the same optimizations in the else block below
        return _asyncify_with_a_sync_executor(func, executor)

    else:
        return _asyncify_with_cf_executor(func, executor)


cdef object _asyncify_with_a_sync_executor(object func, executor: _AsyncExecutorMixin):
    # ASyncExecutor classes are better optimized than normal ones and we can do this
    run = executor.run

    @wraps(func)
    async def _asyncify_wrap_fast(*args, **kwargs):
        return await run(func, *args, **kwargs)
    
    return _asyncify_wrap_fast


cdef object _asyncify_with_cf_executor(object func, executor: Executor):
    cdef object submit
    cdef object loop
    cdef object create_future

    submit = executor.submit

    try:
        loop = get_running_loop()
        create_future = loop.create_future

        @wraps(func)
        async def _asyncify_wrap(*args, **kwargs):
            fut = create_future()
            cf_fut = submit(func, *args, **kwargs)
            _chain_future(cf_fut, fut)
            return await fut

    except RuntimeError:
        loop, create_future = None, None

        @wraps(func)
        async def _asyncify_wrap(*args, **kwargs):
            loop = get_event_loop()
            fut = loop.create_future()
            cf_fut = submit(func, *args, **kwargs)
            _chain_future(cf_fut, fut)
            return await fut

    return _asyncify_wrap
