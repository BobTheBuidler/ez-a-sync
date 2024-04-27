
import asyncio
import functools
import logging

from a_sync._typing import *

if TYPE_CHECKING:
    from a_sync import SmartProcessingQueue


_Args = Tuple[Any]
_Kwargs = Tuple[Tuple[str, Any]]
_Key = Tuple[_Args, _Kwargs]

logger = logging.getLogger(__name__)

class _SmartFutureMixin(Generic[T]):
    _queue: Optional["SmartProcessingQueue[Any, Any, T]"] = None
    def __await__(self):
        logger.debug("entering %s", self)
        if self.done():
            return self.result()  # May raise too.
        self._asyncio_future_blocking = True
        self._waiters.add(current_task := asyncio.current_task(self._loop))
        logger.debug("awaiting %s", self)
        yield self  # This tells Task to wait for completion.
        self._waiters.remove(current_task)
        if self._queue and not self._waiters:
            self._queue._futs.pop(self._key)
        if not self.done():
            raise RuntimeError("await wasn't used with future")
        return self.result()  # May raise too.
    @property
    def num_waiters(self) -> int:
        return sum(getattr(waiter, 'num_waiters', 1) for waiter in self._waiters)
    @functools.cached_property
    def _waiters(self) -> Set["asyncio.Task[T]"]:
        return set()

class SmartFuture(_SmartFutureMixin[T], asyncio.Future):
    def __init__(self, queue: "SmartProcessingQueue", key: _Key, *, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        super().__init__(loop=loop)
        self._queue = queue
        self._key = key
    def __repr__(self):
        return f"<{type(self).__name__} key={self._key} waiters={self.num_waiters} {self._state}>"
    def __lt__(self, other: "SmartFuture") -> bool:
        """heap considers lower values as higher priority so a future with more waiters will be 'less than' a future with less waiters."""
        return self.num_waiters > other.num_waiters

class SmartTask(_SmartFutureMixin[T], asyncio.Task):
    ...

def smart_task_factory(loop: asyncio.AbstractEventLoop, coro: Awaitable[T]) -> SmartTask[T]:
    return SmartTask(coro, loop=loop)

def set_smart_task_factory(loop: asyncio.AbstractEventLoop) -> None:
    asyncio.get_event_loop().set_task_factory(smart_task_factory)