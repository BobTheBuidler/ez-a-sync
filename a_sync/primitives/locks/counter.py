import asyncio
from collections import defaultdict
from typing import Iterable


class CounterLock:
    """
    A asyncio primative that blocks until the internal counter has reached a specific value.
    
    counter = CounterLock()
    A coroutine can now `await counter.wait_for(3)` and it will block until the internal counter >= 3.
    Now if some other task executes `counter.value = 5` or `counter.set(5)`, the first coroutine will unblock as 5 >= 3.
    
    The internal counter can only increase.
    """
    def __init__(self, start_value: int = 0):
        self._value = start_value
        self._conditions = defaultdict(asyncio.Event)
        self.is_ready = lambda v: self._value >= v
        
    async def wait_for(self, value: int) -> bool:
        if not self.is_ready(value):
            await self._conditions[value].wait()
        return True
    
    def set(self, value: int) -> None:
        self.value = value
        
    @property
    def value(self) -> int:
        return self._value
    
    @value.setter
    def value(self, value: int) -> None:
        if value > self._value:
            self._value = value
            ready = [
                self._conditions.pop(key)
                for key in list(self._conditions.keys())
                if key <= self._value
            ]
            for event in ready:
                event.set()
        elif value < self._value:
            raise ValueError("You cannot decrease the value.")

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
    