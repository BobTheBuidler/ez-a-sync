"""
This module provides two specialized async flow management classes, CounterLock and CounterLockCluster.

These primitives manages :class:`asyncio.Task` objects that must wait for an internal counter to reach a specific value.
"""

import asyncio
from collections import defaultdict
from time import time
from typing import DefaultDict, Iterable, Optional

from a_sync.primitives._debug import _DebugDaemonMixin
from a_sync.primitives.locks.event import Event


class CounterLock(_DebugDaemonMixin):
    """
    An async primitive that blocks until the internal counter has reached a specific value.
    
    A coroutine can `await counter.wait_for(3)` and it will block until the internal counter >= 3.
    If some other task executes `counter.value = 5` or `counter.set(5)`, the first coroutine will unblock as 5 >= 3.
    
    The internal counter can only increase.
    """
    __slots__ = "is_ready", "_name", "_value", "_events"
    def __init__(self, start_value: int = 0, name: Optional[str] = None):
        """
        Initializes the CounterLock with a starting value and an optional name.

        Args:
            start_value: The initial value of the counter.
            name (optional): An optional name for the counter, used in debug logs.
        """

        self._name = name
        """An optional name for the counter, used in debug logs."""

        self._value = start_value
        """The current value of the counter."""

        self._events: DefaultDict[int, Event] = defaultdict(Event)
        """A defaultdict that maps each awaited value to an :class:`asyncio.Event` that manages the waiters for that value."""

        self.is_ready = lambda v: self._value >= v
        """A lambda function that indicates whether a given value has already been surpassed."""
        
    async def wait_for(self, value: int) -> bool:
        """
        Waits until the counter reaches or exceeds the specified value.

        Args:
            value: The value to wait for.

        Returns:
            True when the counter reaches or exceeds the specified value.
        """
        if not self.is_ready(value):
            self._ensure_debug_daemon()
            await self._events[value].wait()
        return True
    
    def set(self, value: int) -> None:
        """
        Sets the counter to the specified value.

        Args:
            value: The value to set the counter to. Must be >= the current value.
        
        Raises:
            ValueError: If the new value is less than the current value.
        """
        self.value = value
    
    def __repr__(self) -> str:
        waiters = {v: len(self._events[v]._waiters) for v in sorted(self._events)}
        return f"<CounterLock name={self._name} value={self._value} waiters={waiters}>"
        
    @property
    def value(self) -> int:
        """
        Gets the current value of the counter.

        Returns:
            The current value of the counter.
        """
        return self._value
    
    @value.setter
    def value(self, value: int) -> None:
        """
        Sets the counter to a new value, waking up any waiters if the value increases beyond the value they are awaiting.

        Args:
            value: The new value of the counter.

        Raises:
            ValueError: If the new value is less than the current value.
        """
        if value > self._value:
            self._value = value
            ready = [self._events.pop(key) for key in list(self._events.keys()) if key <= self._value]
            for event in ready:
                event.set()
        elif value < self._value:
            raise ValueError("You cannot decrease the value.")
    
    async def _debug_daemon(self) -> None:
        """
        Periodically logs debug information about the counter state and waiters.
        """
        start = time()
        while self._events:
            self.logger.debug("%s is still locked after %sm", self, round(time() - start / 60, 2))
            await asyncio.sleep(300)

class CounterLockCluster:
    """
    An asyncio primitive that represents 2 or more CounterLock objects.
    
    `wait_for(i)` will block until the value of all CounterLock objects is >= i.
    """
    __slots__ = "locks", 
    def __init__(self, counter_locks: Iterable[CounterLock]) -> None:
        """
        Initializes the CounterLockCluster with a collection of CounterLock objects.

        Args:
            counter_locks: The CounterLock objects to manage.
        """
        self.locks = list(counter_locks)
    
    async def wait_for(self, value: int) -> bool:
        """
        Waits until the value of all CounterLock objects in the cluster reaches or exceeds the specified value.

        Args:
            value: The value to wait for.

        Returns:
            True when the value of all CounterLock objects reach or exceed the specified value.
        """
        await asyncio.gather(*[counter_lock.wait_for(value) for counter_lock in self.locks])
        return True
    