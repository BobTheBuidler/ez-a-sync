"""
This module provides utility functions for handling asynchronous operations
and converting synchronous functions to asynchronous ones.
"""

from asyncio import Future, iscoroutinefunction, new_event_loop, set_event_loop
from asyncio import get_event_loop as _get_event_loop
from asyncio.futures import _convert_future_exc
from functools import wraps

from a_sync import exceptions
from a_sync._typing import *


cpdef object get_event_loop():
    cdef object loop
    try:
        return _get_event_loop()
    except RuntimeError as e:  # Necessary for use with multi-threaded applications.
        if not str(e).startswith("There is no current event loop in thread"):
            raise
        loop = new_event_loop()
        set_event_loop(loop)
    return loop


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
            raise exceptions.SyncModeInAsyncContextError from e.__cause__
        raise


cdef object _asyncify(object func, object executor):  # type: ignore [misc]
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

    if iscoroutinefunction(func) or isinstance(func, ASyncFunction):
        raise exceptions.FunctionNotSync(func)
    
    cdef object sumbit = executor.submit
    
    @wraps(func)
    async def _asyncify_wrap(*args: P.args, **kwargs: P.kwargs) -> T:
        loop = get_event_loop()
        fut = loop.create_future()
        cf_fut = submit(func, *args, **kwargs)
        def _call_copy_future_state(cf_fut: "concurrent.futures.Future"):
            if _fut_is_cancelled(fut):
                return
            loop.call_soon_threadsafe(
                _copy_future_state,
                cf_fut,
                fut,
            )
        cf_fut.add_done_callback(_call_copy_future_state)
        return fut

    return _asyncify_wrap

cpdef void _copy_future_state(cf_fut: concurrent.futures.Future, fut: asyncio.Future):
    """Internal helper to copy state from another Future.

    The other Future may be a concurrent.futures.Future.
    """
    # check this again in case it was cancelled since the last check
    if _fut_is_cancelled(fut):
        return
    exception = _get_exception(cf_fut)
    if exception is None:
        _set_fut_result(fut, _get_result(cf_fut))
    else:
        _set_fut_exception(fut, _convert_future_exc(exception))

cdef object _fut_is_cancelled = Future.cancelled
cdef object _get_result = concurrent.futures.Future.result
cdef object _get_exception = concurrent.futures.Future.exception
cdef object _set_fut_result = Future.set_result
cdef object _set_fut_exception = Future.set_exception
