"""
This module defines smart future and task utilities for the a_sync library.
These utilities provide enhanced functionality for managing asynchronous tasks and futures,
including task shielding and a custom task factory for creating SmartTask instances.
"""

import asyncio
import logging
import warnings
import weakref

import a_sync.asyncio
from a_sync._typing import *

if TYPE_CHECKING:
    from a_sync import SmartProcessingQueue


_Args = Tuple[Any]
_Kwargs = Tuple[Tuple[str, Any]]
_Key = Tuple[_Args, _Kwargs]

logger = logging.getLogger(__name__)


class _SmartFutureMixin(Generic[T]):
    """
    Mixin class that provides common functionality for smart futures and tasks.

    This mixin provides methods for managing waiters and integrating with a smart processing queue.
    """

    _queue: Optional["SmartProcessingQueue[Any, Any, T]"] = None
    _key: _Key
    _waiters: "weakref.WeakSet[SmartTask[T]]"

    def __await__(self: Union["SmartFuture", "SmartTask"]) -> Generator[Any, None, T]:
        """
        Await the smart future or task, handling waiters and logging.
        """
        if self.done():
            return self.result()  # May raise too.
        self._asyncio_future_blocking = True
        self._waiters.add(current_task := asyncio.current_task(self._loop))
        current_task.add_done_callback(self._waiter_done_cleanup_callback)  # type: ignore [union-attr]
        logger.debug("awaiting %s", self)
        yield self  # This tells Task to wait for completion.
        if not self.done():
            raise RuntimeError("await wasn't used with future")
        return self.result()  # May raise too.

    @property
    def num_waiters(self: Union["SmartFuture", "SmartTask"]) -> int:
        # NOTE: we check .done() because the callback may not have ran yet and its very lightweight
        """
        Get the number of waiters currently awaiting the future or task.
        """
        if self.done():
            # if there are any waiters left, there won't be once the event loop runs once
            return 0
        return sum(getattr(waiter, "num_waiters", 1) or 1 for waiter in self._waiters)

    def _waiter_done_cleanup_callback(
        self: Union["SmartFuture", "SmartTask"], waiter: "SmartTask"
    ) -> None:
        """
        Callback to clean up waiters when a waiter task is done.

        Removes the waiter from _waiters, and _queue._futs if applicable
        """
        if not self.done():
            self._waiters.remove(waiter)

    def _self_done_cleanup_callback(self: Union["SmartFuture", "SmartTask"]) -> None:
        """
        Callback to clean up waiters and remove the future from the queue when done.
        """
        self._waiters.clear()
        if queue := self._queue:
            queue._futs.pop(self._key)


class SmartFuture(_SmartFutureMixin[T], asyncio.Future):
    """
    A smart future that tracks waiters and integrates with a smart processing queue.

    Inherits from both _SmartFutureMixin and asyncio.Future, providing additional functionality
    for tracking waiters and integrating with a smart processing queue.
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
        """
        super().__init__(loop=loop)
        if queue:
            self._queue = weakref.proxy(queue)
        if key:
            self._key = key
        self._waiters = weakref.WeakSet()
        self.add_done_callback(SmartFuture._self_done_cleanup_callback)

    def __repr__(self):
        return f"<{type(self).__name__} key={self._key} waiters={self.num_waiters} {self._state}>"

    def __lt__(self, other: "SmartFuture[T]") -> bool:
        """
        Compare the number of waiters to determine priority in a heap.
        Lower values indicate higher priority, so more waiters means 'less than'.

        Args:
            other: Another SmartFuture to compare with.

        Returns:
            True if self has more waiters than other.
        """
        return self.num_waiters > other.num_waiters


def create_future(
    *,
    queue: Optional["SmartProcessingQueue"] = None,
    key: Optional[_Key] = None,
    loop: Optional[asyncio.AbstractEventLoop] = None,
) -> SmartFuture[V]:
    """
    Create a SmartFuture instance.

    Args:
        queue: Optional; a smart processing queue.
        key: Optional; a key identifying the future.
        loop: Optional; the event loop.

    Returns:
        A SmartFuture instance.
    """
    return SmartFuture(queue=queue, key=key, loop=loop or asyncio.get_event_loop())


class SmartTask(_SmartFutureMixin[T], asyncio.Task):
    """
    A smart task that tracks waiters and integrates with a smart processing queue.

    Inherits from both _SmartFutureMixin and asyncio.Task, providing additional functionality
    for tracking waiters and integrating with a smart processing queue.
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
        """
        super().__init__(coro, loop=loop, name=name)
        self._waiters: Set["asyncio.Task[T]"] = set()
        self.add_done_callback(SmartTask._self_done_cleanup_callback)


def smart_task_factory(
    loop: asyncio.AbstractEventLoop, coro: Awaitable[T]
) -> SmartTask[T]:
    """
    Task factory function that an event loop calls to create new tasks.

    This factory function utilizes ez-a-sync's custom :class:`~SmartTask` implementation.

    Args:
        loop: The event loop.
        coro: The coroutine to run in the task.

    Returns:
        A SmartTask instance running the provided coroutine.
    """
    return SmartTask(coro, loop=loop)


def set_smart_task_factory(loop: asyncio.AbstractEventLoop = None) -> None:
    """
    Set the event loop's task factory to :func:`~smart_task_factory` so all tasks will be SmartTask instances.

    Args:
        loop: Optional; the event loop. If None, the current event loop is used.
    """
    if loop is None:
        loop = a_sync.asyncio.get_event_loop()
    loop.set_task_factory(smart_task_factory)


def shield(
    arg: Awaitable[T], *, loop: Optional[asyncio.AbstractEventLoop] = None
) -> SmartFuture[T]:
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
    """
    if loop is not None:
        warnings.warn(
            "The loop argument is deprecated since Python 3.8, "
            "and scheduled for removal in Python 3.10.",
            DeprecationWarning,
            stacklevel=2,
        )
    inner = asyncio.ensure_future(arg, loop=loop)
    if inner.done():
        # Shortcut.
        return inner
    loop = asyncio.futures._get_loop(inner)
    outer = create_future(loop=loop)
    # special handling to connect SmartFutures to SmartTasks if enabled
    if (waiters := getattr(inner, "_waiters", None)) is not None:
        waiters.add(outer)

    def _inner_done_callback(inner):
        if outer.cancelled():
            if not inner.cancelled():
                # Mark inner's result as retrieved.
                inner.exception()
            return

        if inner.cancelled():
            outer.cancel()
        else:
            exc = inner.exception()
            if exc is not None:
                outer.set_exception(exc)
            else:
                outer.set_result(inner.result())

    def _outer_done_callback(outer):
        if not inner.done():
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
