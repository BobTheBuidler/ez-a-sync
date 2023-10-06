import asyncio
from collections import defaultdict
from time import time
from typing import Iterable, Optional

from a_sync.primitives._debug import _DebugDaemonMixin
from a_sync.primitives.locks.event import Event


class CounterLock(_DebugDaemonMixin):
    """
    A asyncio primative that blocks until the internal counter has reached a specific value.
    
    counter = CounterLock()
    A coroutine can now `await counter.wait_for(3)` and it will block until the internal counter >= 3.
    Now if some other task executes `counter.value = 5` or `counter.set(5)`, the first coroutine will unblock as 5 >= 3.
    
    The internal counter can only increase.
    """
    def __init__(self, start_value: int = 0, name: Optional[str] = None):
        self._name = name
        self._value = start_value
        self._events = defaultdict(Event)
        self.is_ready = lambda v: self._value >= v
        
    async def wait_for(self, value: int) -> bool:
        if not self.is_ready(value):
            self._ensure_debug_daemon()
            await self._events[value].wait()
        return True
    
    def set(self, value: int) -> None:
        self.value = value
    
    def __repr__(self) -> str:
        waiters = {v: len(self._events[v]._waiters) for v in sorted(self._events)}
        return f"<CounterLock name={self._name} value={self._value} waiters={waiters}>"
        
    @property
    def value(self) -> int:
        return self._value
    
    @value.setter
    def value(self, value: int) -> None:
        if value > self._value:
            self._value = value
            ready = [self._events.pop(key) for key in list(self._events.keys()) if key <= self._value]
            for event in ready:
                event.set()
        elif value < self._value:
            raise ValueError("You cannot decrease the value.")
    
    async def _debug_daemon(self) -> None:
        start = time()
        while self._events:
            self.logger.debug("%s is still locked after %sm", self, round(time() - start / 60, 2))
            await asyncio.sleep(300)

class CounterLockCluster:
    """
    An asyncio primitive that represents 2 or more CounterLock objects.
    
    `wait_for(i)` will block until the value of all CounterLock objects is >= i.
    """
    def __init__(self, counter_locks: Iterable[CounterLock]) -> None:
        self.locks = list(counter_locks)
    
    async def wait_for(self, value: int) -> bool:
        await asyncio.gather(*[counter_lock.wait_for(value) for counter_lock in self.locks])
        return True
    