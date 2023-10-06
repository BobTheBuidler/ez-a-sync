
import asyncio
import heapq
import logging
from collections import deque
from functools import cached_property
from typing import (Deque, Dict, Generic, List, Literal, Optional, Protocol,
                    Type, TypeVar)

from a_sync.primitives.locks.semaphore import Semaphore

logger = logging.getLogger(__name__)

T = TypeVar('T', covariant=True)

class Priority(Protocol):
    def __lt__(self, other) -> bool:
        ...

PT = TypeVar('PT', bound=Priority)
    
CM = TypeVar('CM', bound="_AbstractPrioritySemaphoreContextManager[Priority]")

class _AbstractPrioritySemaphore(Semaphore, Generic[PT, CM]):
    name: Optional[str]
    _value: int
    _waiters: List["_AbstractPrioritySemaphoreContextManager[PT]"]  # type: ignore [assignment]

    @property
    def _context_manager_class(self) -> Type["_AbstractPrioritySemaphoreContextManager[PT]"]:
        raise NotImplementedError
    
    @property
    def _top_priority(self) -> PT:
        # You can use this so you can set priorities with non numeric comparable values
        raise NotImplementedError

    def __init__(self, value: int = 1, *, name: Optional[str] = None) -> None:
        self._context_managers: Dict[PT, _AbstractPrioritySemaphoreContextManager[PT]] = {}
        self._capacity = value
        super().__init__(value, name=name)
        self._waiters = []
        # NOTE: This should (hopefully) be temporary
        self._potential_lost_waiters = []

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name} capacity={self._capacity} value={self._value} waiters={self._count_waiters()}>"

    async def __aenter__(self) -> None:
        await self[self._top_priority].acquire()

    async def __aexit__(self, *_) -> None:
        self[self._top_priority].release()
    
    async def acquire(self) -> Literal[True]:
        return await self[self._top_priority].acquire()
    
    def __getitem__(self, priority: Optional[PT]) -> "_AbstractPrioritySemaphoreContextManager[PT]":
        priority = self._top_priority if priority is None else priority
        if priority not in self._context_managers:
            context_manager = self._context_manager_class(self, priority, name=self.name)
            heapq.heappush(self._waiters, context_manager)  # type: ignore [misc]
            self._context_managers[priority] = context_manager
        return self._context_managers[priority]

    def locked(self) -> bool:
        """Returns True if semaphore cannot be acquired immediately."""
        return self._value == 0 or (
            any(
                cm._waiters and any(not w.cancelled() for w in cm._waiters) 
                for cm in (self._context_managers.values() or ())
            )
        )
    
    def _count_waiters(self) -> Dict[PT, int]:
        return {manager._priority: len(manager.waiters) for manager in sorted(self._waiters, key=lambda m: m._priority)}
    
    def _wake_up_next(self) -> None:
        while self._waiters:
            manager = heapq.heappop(self._waiters)
            if len(manager) == 0:
                # There are no more waiters, get rid of the empty manager
                logger.debug("manager %s has no more waiters, popping from %s", manager._repr_no_parent_(), self)
                self._context_managers.pop(manager._priority)
                continue
            logger.debug("waking up next for %s", manager._repr_no_parent_())
            
            woke_up = False
            start_len = len(manager)
        
            if not manager._waiters:
                logger.debug('not manager._waiters')
            
            while manager._waiters:
                waiter = manager._waiters.popleft()
                self._potential_lost_waiters.remove(waiter)
                if not waiter.done():
                    waiter.set_result(None)
                    logger.debug("woke up %s", waiter)
                    woke_up = True
                    break
            
            if not woke_up:
                self._context_managers.pop(manager._priority)
                continue
            
            end_len = len(manager)
            
            assert start_len > end_len, f"start {start_len} end {end_len}"
            
            if end_len:
                # There are still waiters, put the manager back
                heapq.heappush(self._waiters, manager)  # type: ignore [misc]
            else:
                # There are no more waiters, get rid of the empty manager
                self._context_managers.pop(manager._priority)
            return
        
        # emergency procedure (hopefully temporary): 
        while self._potential_lost_waiters:
            waiter = self._potential_lost_waiters.pop(0)
            logger.debug('we found a lost waiter %s', waiter)
            if not waiter.done():
                waiter.set_result(None)
                logger.debug("woke up lost waiter %s", waiter)
                return
        logger.debug("%s has no waiters to wake", self)

class _AbstractPrioritySemaphoreContextManager(Semaphore, Generic[PT]):
    _loop: asyncio.AbstractEventLoop
    _waiters: Deque[asyncio.Future]  # type: ignore [assignment]
    
    @property
    def _priority_name(self) -> str:
        raise NotImplementedError
    
    def __init__(self, parent: _AbstractPrioritySemaphore, priority: PT, name: Optional[str] = None) -> None:
        self._parent = parent
        self._priority = priority
        super().__init__(0, name=name)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} parent={self._parent} {self._priority_name}={self._priority} waiters={len(self)}>"
    
    def _repr_no_parent_(self) -> str:
        return f"<{self.__class__.__name__} parent_name={self._parent.name} {self._priority_name}={self._priority} waiters={len(self)}>"
    
    def __lt__(self, other) -> bool:
        if type(other) is not type(self):
            raise TypeError(f"{other} is not type {self.__class__.__name__}")
        return self._priority < other._priority
    
    @cached_property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._loop or asyncio.get_event_loop()
    
    @property
    def waiters (self) -> Deque[asyncio.Future]:
        if self._waiters is None:
            self._waiters = deque()
        return self._waiters
    
    async def acquire(self) -> Literal[True]:
        """Acquire a semaphore.

        If the internal counter is larger than zero on entry,
        decrement it by one and return True immediately.  If it is
        zero on entry, block, waiting until some other coroutine has
        called release() to make it larger than 0, and then return
        True.
        """
        if self._parent._value <= 0:
            self._ensure_debug_daemon()
        while self._parent._value <= 0:
            fut = self.loop.create_future()
            self.waiters.append(fut)
            self._parent._potential_lost_waiters.append(fut)
            try:
                await fut
            except:
                # See the similar code in Queue.get.
                fut.cancel()
                if self._parent._value > 0 and not fut.cancelled():
                    self._parent._wake_up_next()
                raise
        self._parent._value -= 1
        return True
    def release(self) -> None:
        self._parent.release()
    
class _PrioritySemaphoreContextManager(_AbstractPrioritySemaphoreContextManager[int]):
    _priority_name = "priority"

class PrioritySemaphore(_AbstractPrioritySemaphore[int, _PrioritySemaphoreContextManager]):  # type: ignore [type-var]
    _context_manager_class = _PrioritySemaphoreContextManager
    _top_priority = -1
    """
    It's kinda like a regular Semaphore but you must give each waiter a priority:

    ```
    priority_semaphore = PrioritySemaphore(10)

    async with priority_semaphore[priority]:
        await do_stuff()
    ```
    
    You can aenter and aexit this semaphore without a priority and it will process those first. Like so:
    
    ```
    priority_semaphore = PrioritySemaphore(10)
    
    async with priority_semaphore:
        await do_stuff()
    ```
    """
