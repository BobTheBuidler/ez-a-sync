"""
This module defines smart future and task utilities for the a_sync library.
These utilities provide enhanced functionality for managing asynchronous tasks and futures,
including a custom task factory for creating :class:`~SmartTask` instances and a shielding mechanism
to protect tasks from cancellation.
"""

import asyncio
import logging
import warnings
import weakref
from libc.stdint cimport uintptr_t

import a_sync.asyncio
from a_sync._typing import *

if TYPE_CHECKING:
    from a_sync import SmartProcessingQueue


_Args = Tuple[Any]
_Kwargs = Tuple[Tuple[str, Any]]
_Key = Tuple[_Args, _Kwargs]

logger = logging.getLogger(__name__)

cdef Py_ssize_t ZERO = 0
cdef Py_ssize_t ONE = 1

class _SmartFutureMixin(Generic[T]):
    """
    Mixin class that provides common functionality for smart futures and tasks.

    This mixin provides methods for managing waiters and integrating with a smart processing queue.
    It uses weak references to manage resources efficiently.

    Example:
        Creating a SmartFuture and awaiting it:

        ```python
        future = SmartFuture()
        result = await future
        ```

        Creating a SmartTask and awaiting it:

        ```python
        task = SmartTask(coro=my_coroutine())
        result = await task
        ```

    See Also:
        - :class:`SmartFuture`
        - :class:`SmartTask`
    """

    _queue: Optional["SmartProcessingQueue[Any, Any, T]"] = None
    _key: _Key
    _waiters: "weakref.WeakSet[SmartTask[T]]"

    @property
    def num_waiters(self: Union["SmartFuture", "SmartTask"]) -> Py_ssize_t:
        """
        Get the number of waiters currently awaiting the future or task.

        This property checks if the future or task is done to ensure accurate counting
        of waiters, as the callback may not have run yet.

        Example:
            ```python
            future = SmartFuture()
            print(future.num_waiters)
            ```

        See Also:
            - :meth:`_waiter_done_cleanup_callback`
        """
        return count_waiters(self)


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
    _refs: dict[uintptr_t, object]
    """Mapping from object ID to weak reference."""
    
    def __cinit__(self):
        self._refs = {}

    def _gc_callback(self, fut: asyncio.Future) -> None:
        # Callback when a weakly-referenced object is garbage collected
        self._refs.pop(<uintptr_t>id(fut), None)  # Safely remove the item if it exists

    cdef void add(self, fut: asyncio.Future):
        # Keep a weak reference with a callback for when the item is collected
        ref = weakref.ref(fut, self._gc_callback)
        self._refs[<uintptr_t>id(fut)] = ref

    cdef void remove(self, fut: asyncio.Future):
        # Keep a weak reference with a callback for when the item is collected
        try:
            self._refs.pop(<uintptr_t>id(fut))
        except KeyError:
            raise KeyError(fut) from None

    def __len__(self) -> int:
        return len(self._refs)

    def __bool__(self) -> bool:
        return bool(self._refs)

    def __contains__(self, item: asyncio.Future) -> bool:
        ref = self._refs.get(<uintptr_t>id(item))
        return ref is not None and ref() is item

    def __iter__(self):
        for ref in self._refs.values():
            item = ref()
            if item is not None:
                yield item

    def __repr__(self):
        # Use list comprehension syntax within the repr function for clarity
        return f"WeakSet({', '.join(repr(item) for item in self)})"


cdef inline bint _is_done(fut: asyncio.Future):
    """Return True if the future is done.

    Done means either that a result / exception are available, or that the
    future was cancelled.
    """
    return <str>fut._state != "PENDING"

cdef inline bint _is_not_done(fut: asyncio.Future):
    """Return False if the future is done.

    Done means either that a result / exception are available, or that the
    future was cancelled.
    """
    return <str>fut._state == "PENDING"

cdef inline bint _is_cancelled(fut: asyncio.Future):
    """Return True if the future was cancelled."""
    return <str>fut._state == "CANCELLED"

cdef object _get_result(fut: asyncio.Future):
    """Return the result this future represents.

    If the future has been cancelled, raises CancelledError.  If the
    future's result isn't yet available, raises InvalidStateError.  If
    the future is done and has an exception set, this exception is raised.
    """
    cdef str state = fut._state
    if state == "FINISHED":
        fut._Future__log_traceback = False
        exc = fut._exception
        if exc is not None:
            raise exc.with_traceback(exc.__traceback__)
        return fut._result
    if state == "CANCELLED":
        raise fut._make_cancelled_error()
    raise asyncio.exceptions.InvalidStateError('Result is not ready.')

cdef object _get_exception(fut: asyncio.Future):
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
    raise asyncio.exceptions.InvalidStateError('Exception is not set.')

_init = asyncio.Future.__init__

class SmartFuture(_SmartFutureMixin[T], asyncio.Future):
    """
    A smart future that tracks waiters and integrates with a smart processing queue.

    Inherits from both :class:`_SmartFutureMixin` and :class:`asyncio.Future`, providing additional functionality
    for tracking waiters and integrating with a smart processing queue.

    Example:
        Creating and awaiting a SmartFuture:

        ```python
        future = SmartFuture()
        await future
        ```

    See Also:
        - :class:`_SmartFutureMixin`
        - :class:`asyncio.Future`
    """

    _queue = None
    _key = None

    def __init__(
        self,
        *,
        queue: Optional["SmartProcessingQueue[Any, Any, T]"],
        key: Optional[_Key] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
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
        _init(self, loop=loop)
        if queue:
            self._queue = weakref.proxy(queue)
            self.add_done_callback(SmartFuture._self_done_cleanup_callback)
        if key:
            self._key = key
        self._waiters = WeakSet()

    def __repr__(self):
        return f"<{<str>type(self).__name__} key={self._key} waiters={count_waiters(self)} {<str>self._state}>"

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

    def __await__(self: Union["SmartFuture", "SmartTask"]) -> Generator[Any, None, T]:
        """
        Await the smart future or task, handling waiters and logging.

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
        if current_task := asyncio.current_task(self._loop):
            (<WeakSet>self._waiters).add(current_task)
            current_task.add_done_callback(
                self._waiter_done_cleanup_callback  # type: ignore [union-attr]
            )

        logger.debug("awaiting %s", self)
        yield self  # This tells Task to wait for completion.
        if _is_not_done(self):
            raise RuntimeError("await wasn't used with future")
        return _get_result(self)  # May raise too.

    def _waiter_done_cleanup_callback(
        self: Union["SmartFuture", "SmartTask"], waiter: "SmartTask"
    ) -> None:
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

    def _self_done_cleanup_callback(self: Union["SmartFuture", "SmartTask"]) -> None:
        """
        Callback to clean up waiters and remove the future from the queue when done.

        This method clears all waiters and removes the future from the associated queue.
        """
        if queue := self._queue:
            queue._futs.pop(self._key)


def create_future(
    *,
    queue: Optional["SmartProcessingQueue"] = None,
    key: Optional[_Key] = None,
    loop: Optional[asyncio.AbstractEventLoop] = None,
) -> SmartFuture[V]:
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
    return SmartFuture(queue=queue, key=key, loop=loop or asyncio.get_event_loop())


class SmartTask(_SmartFutureMixin[T], asyncio.Task):
    """
    A smart task that tracks waiters and integrates with a smart processing queue.

    Inherits from both :class:`_SmartFutureMixin` and :class:`asyncio.Task`, providing additional functionality
    for tracking waiters and integrating with a smart processing queue.

    Example:
        Creating and awaiting a SmartTask:

        ```python
        task = SmartTask(coro=my_coroutine())
        await task
        ```

    See Also:
        - :class:`_SmartFutureMixin`
        - :class:`asyncio.Task`
    """

    def __init__(
        self,
        coro: Awaitable[T],
        *,
        loop: Optional[asyncio.AbstractEventLoop] = None,
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
        asyncio.Task.__init__(self, coro, loop=loop, name=name)
        self._waiters: Set["asyncio.Task[T]"] = <set>set()
        self.add_done_callback(SmartTask._self_done_cleanup_callback)

    def __await__(self: Union["SmartFuture", "SmartTask"]) -> Generator[Any, None, T]:
        """
        Await the smart future or task, handling waiters and logging.

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
        if current_task := asyncio.current_task(self._loop):
            (<set>self._waiters).add(current_task)
            current_task.add_done_callback(
                self._waiter_done_cleanup_callback  # type: ignore [union-attr]
            )

        logger.debug("awaiting %s", self)
        yield self  # This tells Task to wait for completion.
        if _is_not_done(self):
            raise RuntimeError("await wasn't used with future")
        return _get_result(self)  # May raise too.

    def _waiter_done_cleanup_callback(
        self: Union["SmartFuture", "SmartTask"], waiter: "SmartTask"
    ) -> None:
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

    def _self_done_cleanup_callback(self: Union["SmartFuture", "SmartTask"]) -> None:
        """
        Callback to clean up waiters and remove the future from the queue when done.

        This method clears all waiters and removes the future from the associated queue.
        """
        (<set>self._waiters).clear()
        if queue := self._queue:
            queue._futs.pop(self._key)


def smart_task_factory(loop: asyncio.AbstractEventLoop, coro: Awaitable[T]) -> SmartTask[T]:
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
    return SmartTask(coro, loop=loop)


def set_smart_task_factory(loop: asyncio.AbstractEventLoop = None) -> None:
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
        loop = a_sync.asyncio.get_event_loop()
    loop.set_task_factory(smart_task_factory)


def shield(
    arg: Awaitable[T], *, loop: Optional[asyncio.AbstractEventLoop] = None
) -> Union[SmartFuture[T], asyncio.Future]:
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
    if loop is not None:
        warnings.warn(
            "The loop argument is deprecated since Python 3.8, "
            "and scheduled for removal in Python 3.10.",
            DeprecationWarning,
            stacklevel=2,
        )
    inner = asyncio.ensure_future(arg, loop=loop)
    if _is_done(inner):
        # Shortcut.
        return inner
    loop = asyncio.futures._get_loop(inner)
    outer = create_future(loop=loop)
    # special handling to connect SmartFutures to SmartTasks if enabled
    if (waiters := getattr(inner, "_waiters", None)) is not None:
        waiters.add(outer)

    def _inner_done_callback(inner):
        if _is_cancelled(outer):
            if not _is_cancelled(inner):
                # Mark inner's result as retrieved.
                _get_exception(inner)
            return

        if _is_cancelled(inner):
            outer.cancel()
        else:
            exc = _get_exception(inner)
            if exc is not None:
                outer.set_exception(exc)
            else:
                outer.set_result(_get_result(inner))

    def _outer_done_callback(outer):
        if _is_not_done(inner):
            inner.remove_done_callback(_inner_done_callback)

    inner.add_done_callback(_inner_done_callback)
    outer.add_done_callback(_outer_done_callback)
    return outer


__all__ = [
    "create_future",
    "shield",
    "SmartFuture",
    "SmartTask",
    "smart_task_factory",
    "set_smart_task_factory",
]
