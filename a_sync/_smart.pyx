"""
This module defines smart future and task utilities for the a_sync library.
These utilities provide enhanced functionality for managing asynchronous tasks and futures,
including a custom task factory for creating :class:`~SmartTask` instances and a shielding mechanism
to protect tasks from cancellation.
"""

import asyncio
import typing
import weakref
from logging import getLogger
from types import TracebackType
from typing import Awaitable, Generator, Optional, Set

cimport cython
from cpython.object cimport PyObject
from cpython.ref cimport Py_DECREF, Py_INCREF
from cpython.unicode cimport PyUnicode_CompareWithASCIIString
from cpython.version cimport PY_VERSION_HEX

from a_sync._typing import T

if typing.TYPE_CHECKING:
    from a_sync import SmartProcessingQueue

cdef extern from "weakrefobject.h":
    PyObject* PyWeakref_NewRef(PyObject*, PyObject*)
    PyObject* PyWeakref_NewProxy(PyObject*, PyObject*)

cdef extern from "pythoncapi_compat.h":
    int PyWeakref_GetRef(PyObject*, PyObject**)
    
# cdef asyncio
cdef object ensure_future = asyncio.ensure_future
cdef object get_event_loop = asyncio.get_event_loop
cdef object AbstractEventLoop = asyncio.AbstractEventLoop
cdef object Future = asyncio.Future
cdef object Task = asyncio.Task
cdef object CancelledError = asyncio.CancelledError
cdef object InvalidStateError = asyncio.InvalidStateError
cdef dict[object, object] _current_tasks = asyncio.tasks._current_tasks
cdef object _future_init = asyncio.Future.__init__
cdef object _get_loop = asyncio.futures._get_loop
cdef object _task_init = asyncio.Task.__init__

# cdef logging
cdef public object logger = getLogger(__name__)
cdef object DEBUG = 10
cdef bint _DEBUG_LOGS_ENABLED = logger.isEnabledFor(DEBUG)
cdef object _logger_log = logger._log
del getLogger

# cdef typing
cdef object Any = typing.Any
cdef object Generic = typing.Generic
cdef object Tuple = typing.Tuple
cdef object Union = typing.Union
del typing


cdef object Args = Tuple[Any]
cdef object Kwargs = Tuple[Tuple[str, Any]]
_Key = Tuple[Args, Kwargs]
cdef object Key = _Key


cdef Py_ssize_t ZERO = 0
cdef Py_ssize_t ONE = 1
cdef PyObject *NONE = <PyObject*>None


cdef void log_await(object arg):
    _logger_log(DEBUG, "awaiting %s", (arg, ))


@cython.linetrace(False)
cdef Py_ssize_t count_waiters(fut: Union["SmartFuture", "SmartTask"]):
    if _is_done(fut):
        return ZERO
    try:
        waiters = fut._waiters
    except AttributeError:
        return ONE
    cdef Py_ssize_t count = ZERO
    for waiter in waiters:
        count += count_waiters(waiter)
    return count


cdef class WeakSet:
    cdef readonly dict _refs
    """Mapping from object ID to weak reference."""

    cdef PyObject *__callback_ptr
    
    def __cinit__(self):
        self._refs = {}

    def __init__(self):
        cdef object gc_callback = self._gc_callback
        self.__callback_ptr = <PyObject*>gc_callback
        Py_INCREF(gc_callback)

    def __dealloc__(self):
        cdef PyObject *callback_ptr = self.__callback_ptr
        if callback_ptr is not NULL:
            Py_DECREF(<object>callback_ptr)
    
    def __repr__(self):
        # Use list comprehension syntax within the repr function for clarity
        return f"WeakSet({', '.join(map(repr, self))})"

    @cython.linetrace(False)
    def __bool__(self) -> bool:
        return bool(self._refs)

    @cython.linetrace(False)
    def __len__(self) -> int:
        return len(self._refs)

    @cython.linetrace(False)
    def __contains__(self, item: Future) -> bool:
        ref = self._refs.get(id(item))
        return ref is not None and ref() is item

    cdef void add(self, fut: Future):
        # Keep a weak reference with a callback for when the item is collected
        cdef PyObject *fut_ptr = <PyObject*>fut
        cdef PyObject *weakref_ptr = PyWeakref_NewRef(fut_ptr, self.__callback_ptr)
        if weakref_ptr == NULL:
            raise MemoryError("Could not create ref")
        self._refs[id(fut)] = <object>weakref_ptr

    cdef void remove(self, fut: Future):
        # Keep a weak reference with a callback for when the item is collected
        try:
            self._refs.pop(id(fut))
        except KeyError:
            raise KeyError(fut) from None

    @cython.linetrace(False)
    def __iter__(self):
        cdef PyObject *obj_ptr = NULL
        for ref in self._refs.values():
            if PyWeakref_GetRef(<PyObject*>ref, &obj_ptr) == 1:
                yield <object>obj_ptr

    @cython.linetrace(False)
    cdef void _gc_callback(self, fut: Future):
        # Callback when a weakly-referenced object is garbage collected
        self._refs.pop(id(fut), None)  # Safely remove the item if it exists


@cython.linetrace(False)
cdef inline bint _is_done(fut: Future):
    """Return True if the future is done.

    Done means either that a result / exception are available, or that the
    future was cancelled.
    """
    return PyUnicode_CompareWithASCIIString(fut._state, b"PENDING") != 0


@cython.linetrace(False)
cdef inline bint _is_not_done(fut: Future):
    """Return False if the future is done.

    Done means either that a result / exception are available, or that the
    future was cancelled.
    """
    return PyUnicode_CompareWithASCIIString(fut._state, b"PENDING") == 0


@cython.linetrace(False)
cdef inline bint _is_cancelled(fut: Future):
    """Return True if the future was cancelled."""
    return PyUnicode_CompareWithASCIIString(fut._state, b"CANCELLED") == 0


@cython.linetrace(False)
cdef object _get_result(fut: Union["SmartFuture", "SmartTask"]):
    """Return the result this future represents.

    If the future has been cancelled, raises CancelledError.  If the
    future's result isn't yet available, raises InvalidStateError.  If
    the future is done and has an exception set, this exception is raised.
    """
    cdef str state = fut._state
    if PyUnicode_CompareWithASCIIString(state, b"FINISHED") == 0:
        exc = fut._exception
        if exc is not None:
            cached_traceback = fut.__traceback__
            if cached_traceback is None:
                fut._Future__log_traceback = False
                cached_traceback = exc.__traceback__
                fut.__traceback__ = cached_traceback
            raise exc.with_traceback(cached_traceback) from exc.__cause__
        return fut._result
    if PyUnicode_CompareWithASCIIString(state, b"CANCELLED") == 0:
        raise (
            CancelledError()
            if PY_VERSION_HEX < 0x03090000  # Python 3.9
            else fut._make_cancelled_error()
        )
    raise InvalidStateError('Result is not ready.')

@cython.linetrace(False)
cdef object _get_exception(fut: Future):
    """Return the exception that was set on this future.

    The exception (or None if no exception was set) is returned only if
    the future is done.  If the future has been cancelled, raises
    CancelledError.  If the future isn't done yet, raises
    InvalidStateError.
    """
    cdef str state = fut._state
    if PyUnicode_CompareWithASCIIString(state, b"FINISHED") == 0:
        fut._Future__log_traceback = False
        return fut._exception
    if PyUnicode_CompareWithASCIIString(state, b"CANCELLED") == 0:
        raise (
            CancelledError()
            if PY_VERSION_HEX < 0x03090000  # Python 3.9
            else fut._make_cancelled_error()
        )
    raise InvalidStateError('Exception is not set.')


class SmartFuture(Future, Generic[T]):
    """
    A smart future that tracks waiters and integrates with a smart processing queue.

    Inherits from :class:`asyncio.Future`, providing additional functionality for tracking waiters and integrating with a smart processing queue.

    Example:
        Creating and awaiting a SmartFuture:

        ```python
        future = SmartFuture()
        await future
        ```

    See Also:
        - :class:`asyncio.Future`
    """
    _queue: Optional["SmartProcessingQueue[Any, Any, T]"] = None
    _key: Optional[Key] = None
    
    _waiters: "weakref.WeakSet[SmartTask[T]]"
    
    __traceback__: Optional[TracebackType] = None

    def __init__(
        self,
        *,
        queue: Optional["SmartProcessingQueue[Any, Any, T]"] = None,
        key: Optional[Key] = None,
        loop: Optional[AbstractEventLoop] = None,
    ) -> None:
        """
        Initialize the SmartFuture with an optional queue and key.

        Args:
            queue: Optional; a smart processing queue.
            key: Optional; a key identifying the future.
            loop: Optional; the event loop.

        Example:
            ```python
            future = SmartFuture(queue=my_queue, key=my_key)
            ```

        See Also:
            - :class:`SmartProcessingQueue`
        """
        cdef PyObject *queue_ptr
        cdef PyObject *proxy_ptr
        _future_init(self, loop=loop)
        if queue:
            queue_ptr = <PyObject*>queue
            proxy_ptr = PyWeakref_NewProxy(queue_ptr, NONE)
            if proxy_ptr == NULL:
                raise MemoryError("Could not create proxy")
            self._queue = <object>proxy_ptr
        if key:
            self._key = key
        self._waiters = WeakSet()

    def __repr__(self):
        return f"<{type(self).__name__} key={self._key} waiters={count_waiters(self)} {<str>self._state}>"

    def __lt__(self, other: "SmartFuture[T]") -> bint:
        """
        Compare the number of waiters to determine priority in a heap.
        Lower values indicate higher priority, so more waiters means 'less than'.

        Args:
            other: Another SmartFuture to compare with.

        Example:
            ```python
            future1 = SmartFuture()
            future2 = SmartFuture()
            print(future1 < future2)
            ```

        See Also:
            - :meth:`num_waiters`
        """
        return count_waiters(self) > count_waiters(other)

    def __await__(self) -> Generator[Any, None, T]:
        """
        Await the future, handling waiters and logging.

        Yields:
            The result of the future or task.

        Raises:
            RuntimeError: If await wasn't used with future.

        Example:
            Awaiting a SmartFuture:

            ```python
            future = SmartFuture()
            result = await future
            ```

            Awaiting a SmartTask:

            ```python
            task = SmartTask(coro=my_coroutine())
            result = await task
            ```
        """
        if _is_done(self):
            return _get_result(self)  # May raise too.

        self._asyncio_future_blocking = True
        if task := current_task(self._loop):
            (<WeakSet>self._waiters).add(task)
            task.add_done_callback(
                self._waiter_done_cleanup_callback  # type: ignore [union-attr]
            )

        if _DEBUG_LOGS_ENABLED:
            log_await(self)
        yield self  # This tells Task to wait for completion.
        if _is_not_done(self):
            raise RuntimeError("await wasn't used with future")

        # remove the future from the associated queue, if any
        if queue := self._queue:
            queue._futs.pop(self._key, None)
        return _get_result(self)  # May raise too.

    @cython.linetrace(False)
    def _waiter_done_cleanup_callback(self, waiter: "SmartTask") -> None:
        """
        Callback to clean up waiters when a waiter task is done.

        Removes the waiter from _waiters, and _queue._futs if applicable.

        Args:
            waiter: The waiter task to clean up.

        Example:
            Automatically called when a waiter task completes.
        """
        if _is_not_done(self):
            (<WeakSet>self._waiters).remove(waiter)


cdef object _SmartFuture = SmartFuture


@cython.linetrace(False)
cdef inline object current_task(object loop):
    return _current_tasks.get(loop)


@cython.linetrace(False)
cpdef inline object create_future(
    queue: Optional["SmartProcessingQueue"] = None,
    key: Optional[Key] = None,
    loop: Optional[AbstractEventLoop] = None,
):
    """
    Create a :class:`~SmartFuture` instance.

    Args:
        queue: Optional; a smart processing queue.
        key: Optional; a key identifying the future.
        loop: Optional; the event loop.

    Returns:
        A SmartFuture instance.

    Example:
        Creating a SmartFuture using the factory function:

        ```python
        future = create_future(queue=my_queue, key=my_key)
        ```

    See Also:
        - :class:`SmartFuture`
    """
    return _SmartFuture(queue=queue, key=key, loop=loop or get_event_loop())


class SmartTask(Task, Generic[T]):
    """
    A smart task that tracks waiters and integrates with a smart processing queue.

    Inherits from :class:`asyncio.Task`, providing additional functionality for tracking waiters.

    Example:
        Creating and awaiting a SmartTask:

        ```python
        task = SmartTask(coro=my_coroutine())
        await task
        ```

    See Also:
        - :class:`asyncio.Task`
    """
    
    _waiters: Set["Task[T]"]
    
    __traceback__: Optional[TracebackType] = None

    @cython.linetrace(False)
    def __init__(
        self,
        coro: Awaitable[T],
        *,
        loop: Optional[AbstractEventLoop] = None,
        name: Optional[str] = None,
    ) -> None:
        """
        Initialize the SmartTask with a coroutine and optional event loop.

        Args:
            coro: The coroutine to run in the task.
            loop: Optional; the event loop.
            name: Optional; the name of the task.

        Example:
            ```python
            task = SmartTask(coro=my_coroutine(), name="my_task")
            ```

        See Also:
            - :func:`asyncio.create_task`
        """
        _task_init(self, coro, loop=loop, name=name)
        self._waiters = set()

    def __await__(self) -> Generator[Any, None, T]:
        """
        Await the task, handling waiters and logging.

        Yields:
            The result of the future or task.

        Raises:
            RuntimeError: If await wasn't used with future.

        Example:
            Awaiting a SmartFuture:

            ```python
            future = SmartFuture()
            result = await future
            ```

            Awaiting a SmartTask:

            ```python
            task = SmartTask(coro=my_coroutine())
            result = await task
            ```
        """
        if _is_done(self):
            return _get_result(self)  # May raise too.

        self._asyncio_future_blocking = True
        if task := current_task(self._loop):
            (<set>self._waiters).add(task)
            task.add_done_callback(
                self._waiter_done_cleanup_callback  # type: ignore [union-attr]
            )

        if _DEBUG_LOGS_ENABLED:
            log_await(self)
        yield self  # This tells Task to wait for completion.
        if _is_not_done(self):
            raise RuntimeError("await wasn't used with future")
            
        # clear the waiters
        self._waiters = set()
        return _get_result(self)  # May raise too.

    @cython.linetrace(False)
    def _waiter_done_cleanup_callback(self, waiter: "SmartTask") -> None:
        """
        Callback to clean up waiters when a waiter task is done.

        Removes the waiter from _waiters, and _queue._futs if applicable.

        Args:
            waiter: The waiter task to clean up.

        Example:
            Automatically called when a waiter task completes.
        """
        if _is_not_done(self):
            (<set>self._waiters).remove(waiter)


cdef object _SmartTask = SmartTask


@cython.linetrace(False)
cpdef object smart_task_factory(loop: AbstractEventLoop, coro: Awaitable[T]):
    """
    Task factory function that an event loop calls to create new tasks.

    This factory function utilizes ez-a-sync's custom :class:`~SmartTask` implementation.

    Args:
        loop: The event loop.
        coro: The coroutine to run in the task.

    Returns:
        A SmartTask instance running the provided coroutine.

    Example:
        Using the smart task factory to create a SmartTask:

        ```python
        loop = asyncio.get_event_loop()
        task = smart_task_factory(loop, my_coroutine())
        ```

    See Also:
        - :func:`set_smart_task_factory`
        - :class:`SmartTask`
    """
    return _SmartTask(coro, loop=loop)


def set_smart_task_factory(loop: AbstractEventLoop = None) -> None:
    """
    Set the event loop's task factory to :func:`~smart_task_factory` so all tasks will be SmartTask instances.

    Args:
        loop: Optional; the event loop. If None, the current event loop is used.

    Example:
        Setting the smart task factory for the current event loop:

        ```python
        set_smart_task_factory()
        ```

    See Also:
        - :func:`smart_task_factory`
    """
    if loop is None:
        import a_sync.asyncio
        loop = a_sync.asyncio.get_event_loop()
    loop.set_task_factory(smart_task_factory)


cpdef object shield(arg: Awaitable[T]):
    """
    Wait for a future, shielding it from cancellation.

    The statement

        res = await shield(something())

    is exactly equivalent to the statement

        res = await something()

    *except* that if the coroutine containing it is cancelled, the
    task running in something() is not cancelled.  From the POV of
    something(), the cancellation did not happen.  But its caller is
    still cancelled, so the yield-from expression still raises
    CancelledError.  Note: If something() is cancelled by other means
    this will still cancel shield().

    If you want to completely ignore cancellation (not recommended)
    you can combine shield() with a try/except clause, as follows:

        try:
            res = await shield(something())
        except CancelledError:
            res = None

    Args:
        arg: The awaitable to shield from cancellation.
        loop: Optional; the event loop. Deprecated since Python 3.8.

    Returns:
        A :class:`SmartFuture` or :class:`asyncio.Future` instance.

    Example:
        Using shield to protect a coroutine from cancellation:

        ```python
        result = await shield(my_coroutine())
        ```

    See Also:
        - :func:`asyncio.shield`
    """
    inner = ensure_future(arg)
    if _is_done(inner):
        # Shortcut.
        return inner

    loop = _get_loop(inner)
    outer = _SmartFuture(loop=loop)

    # special handling to connect SmartFutures to SmartTasks if enabled
    if (waiters := getattr(inner, "_waiters", None)) is not None:
        waiters.add(outer)

    _inner_done_callback, _outer_done_callback = _get_done_callbacks(inner, outer)

    inner.add_done_callback(_inner_done_callback)
    outer.add_done_callback(_outer_done_callback)
    return outer


cdef tuple _get_done_callbacks(inner: Task, outer: Future):

    def _inner_done_callback(inner):
        if _is_cancelled(outer):
            if not _is_cancelled(inner):
                # Mark inner's result as retrieved.
                inner._Future__log_traceback = False
            return

        if _is_cancelled(inner):
            outer.cancel()
        else:
            exc = _get_exception(inner)
            if exc is not None:
                outer.set_exception(exc)
            else:
                outer.set_result(inner._result)

    def _outer_done_callback(outer):
        if _is_not_done(inner):
            inner.remove_done_callback(_inner_done_callback)
    
    return _inner_done_callback, _outer_done_callback


__all__ = [
    "create_future",
    "shield",
    "SmartFuture",
    "SmartTask",
    "smart_task_factory",
    "set_smart_task_factory",
]
