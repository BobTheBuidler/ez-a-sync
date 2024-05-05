
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
    _queue: Optional["SmartProcessingQueue[Any, Any, T]"] = None
    _key: _Key
    _waiters: "weakref.WeakSet[SmartTask[T]]"
    def __await__(self: "SmartFuture"):
        if self.done():
            return self.result()  # May raise too.
        self._asyncio_future_blocking = True
        self._waiters.add(current_task := asyncio.current_task(self._loop))
        current_task.add_done_callback(self._waiter_done_cleanup_callback)
        logger.debug("awaiting %s", self)
        yield self  # This tells Task to wait for completion.
        if not self.done():
            raise RuntimeError("await wasn't used with future")
        return self.result()  # May raise too.
    @property
    def num_waiters(self: "SmartFuture") -> int:
        # NOTE: we check .done() because the callback may not have ran yet and its very lightweight
        if self.done():
            # if there are any waiters left, there won't be once the event loop runs once
            return 0
        return sum(getattr(waiter, 'num_waiters', 1) or 1 for waiter in self._waiters)
    def _waiter_done_cleanup_callback(self: "SmartFuture", waiter: "SmartTask") -> None:
        "Removes the waiter from _waiters, and _queue._futs if applicable"
        if not self.done():
            self._waiters.remove(waiter)
    def _self_done_cleanup_callback(self: "SmartFuture") -> None:
        self._waiters.clear()
        if queue := self._queue:
            queue._futs.pop(self._key)


class SmartFuture(_SmartFutureMixin[T], asyncio.Future):
    _queue = None
    _key = None
    def __init__(
        self, 
        *, 
        queue: Optional["SmartProcessingQueue[Any, Any, T]"], 
        key: Optional[_Key] = None, 
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
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
        """heap considers lower values as higher priority so a future with more waiters will be 'less than' a future with less waiters."""
        #other = other_ref()
        #if other is None:
        #    # garbage collected refs should always process first so they can be popped from the queue
        #    return False
        return self.num_waiters > other.num_waiters

def create_future(
    *,
    queue: Optional["SmartProcessingQueue"] = None, 
    key: Optional[_Key] = None, 
    loop: Optional[asyncio.AbstractEventLoop] = None,
) -> SmartFuture[V]:
    return SmartFuture(queue=queue, key=key, loop=loop or asyncio.get_event_loop())

class SmartTask(_SmartFutureMixin[T], asyncio.Task):
    def __init__(
        self, 
        coro: Awaitable[T], 
        *, 
        loop: Optional[asyncio.AbstractEventLoop] = None, 
        name: Optional[str] = None,
    ) -> None:
        super().__init__(coro, loop=loop, name=name)
        self._waiters: Set["asyncio.Task[T]"] = set()
        self.add_done_callback(SmartTask._self_done_cleanup_callback)

def smart_task_factory(loop: asyncio.AbstractEventLoop, coro: Awaitable[T]) -> SmartTask[T]:
    return SmartTask(coro, loop=loop)

def set_smart_task_factory(loop: asyncio.AbstractEventLoop = None) -> None:
    if loop is None:
        loop = a_sync.asyncio.get_event_loop()
    loop.set_task_factory(smart_task_factory)

def shield(arg: Awaitable[T], *, loop: Optional[asyncio.AbstractEventLoop] = None) -> SmartFuture[T]:
    """Wait for a future, shielding it from cancellation.

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
    """
    if loop is not None:
        warnings.warn("The loop argument is deprecated since Python 3.8, "
                      "and scheduled for removal in Python 3.10.",
                      DeprecationWarning, stacklevel=2)
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


__all__ = ["create_future", "shield", "SmartFuture", "SmartTask", "smart_task_factory", "set_smart_task_factory"]
