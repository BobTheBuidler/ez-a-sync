"""
This module provides two specialized async flow management classes, :class:`CounterLock` and :class:`CounterLockCluster`.

These primitives manage synchronization of tasks that must wait for an internal counter to reach a specific value.
"""

import asyncio
from collections import defaultdict
from libc.string cimport strcpy
from libc.stdlib cimport malloc, free
from libc.time cimport time
from typing import DefaultDict, Iterable

from a_sync.primitives._debug cimport _DebugDaemonMixin
from a_sync.primitives.locks.event cimport CythonEvent as Event

cdef extern from "time.h":
    ctypedef long time_t


cdef class CounterLock(_DebugDaemonMixin):
    """
    An async primitive that uses an internal counter to manage task synchronization.

    A coroutine can `await counter.wait_for(3)` and it will wait until the internal counter >= 3.
    If some other task executes `counter.value = 5` or `counter.set(5)`, the first coroutine will proceed as 5 >= 3.

    The internal counter can only be set to a value greater than the current value.

    See Also:
        :class:`CounterLockCluster` for managing multiple :class:`CounterLock` instances.
    """

    def __init__(self, start_value: int = 0, str name = ""):
        """
        Initializes the :class:`CounterLock` with a starting value and an optional name.

        Args:
            start_value: The initial value of the counter.
            name: An optional name for the counter, used in debug logs.

        Examples:
            >>> counter = CounterLock(start_value=0, name="example_counter")
            >>> counter.value
            0
        """
        # we need a constant to coerce to char*
        cdef bytes encoded_name = name.encode("utf-8")
        cdef Py_ssize_t length = len(encoded_name)

        # Allocate memory for the char* and add 1 for the null character
        self.__name = <char*>malloc(length + 1)
        """An optional name for the counter, used in debug logs."""

        if self.__name == NULL:
            raise MemoryError("Failed to allocate memory for __name.")
        # Copy the bytes data into the char*
        strcpy(self.__name, encoded_name)

        self._value = start_value
        """The current value of the counter."""

        self._events: DefaultDict[int, Event] = defaultdict(Event)
        """A defaultdict that maps each awaited value to an :class:`Event` that manages the waiters for that value."""

        self.is_ready = lambda v: self._value >= v
        """A lambda function that indicates whether the current counter value is greater than or equal to a given value."""

    def __dealloc__(self):
        # Free the memory allocated for __name
        if self.__name is not NULL:
            free(self.__name)

    def __repr__(self) -> str:
        """
        Returns a string representation of the :class:`CounterLock` instance.

        The representation includes the name, current value, and the number of waiters for each awaited value.

        Examples:
            >>> counter = CounterLock(start_value=0, name="example_counter")
            >>> repr(counter)
            '<CounterLock name=example_counter value=0 waiters={}>'
        """
        cdef dict[int, Py_ssize_t] waiters = {v: len(self._events[v]._waiters) for v in sorted(self._events)}
        return "<CounterLock name={} value={} waiters={}>".format(self.__name.decode("utf-8"), self._value, waiters)

    async def wait_for(self, value: int) -> bool:
        """
        Waits until the counter reaches or exceeds the specified value.

        This method will ensure the debug daemon is running if the counter is not ready.

        Args:
            value: The value to wait for.

        Examples:
            >>> counter = CounterLock(start_value=0)
            >>> await counter.wait_for(5)  # This will block until counter.value >= 5

        See Also:
            :meth:`CounterLock.set` to set the counter value.
        """
        if not self.is_ready(value):
            self._ensure_debug_daemon()
            await self._events[value].c_wait()
        return True

    cpdef void set(self, int value):
        """
        Sets the counter to the specified value.

        This method internally uses the `value` property to enforce that the new value must be strictly greater than the current value.

        Args:
            value: The value to set the counter to. Must be strictly greater than the current value.

        Raises:
            ValueError: If the new value is less than or equal to the current value.

        Examples:
            >>> counter = CounterLock(start_value=0)
            >>> counter.set(5)
            >>> counter.value
            5

        See Also:
            :meth:`CounterLock.value` for direct value assignment.
        """
        self.c_set(value)

    @property
    def value(self) -> int:
        """
        Gets the current value of the counter.

        Examples:
            >>> counter = CounterLock(start_value=0)
            >>> counter.value
            0
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

        Examples:
            >>> counter = CounterLock(start_value=0)
            >>> counter.value = 5
            >>> counter.value
            5
            >>> counter.value = 3
            Traceback (most recent call last):
            ...
            ValueError: You cannot decrease the value.
        """
        self.c_set(value)

    cdef void c_set(self, int value):
        if value > self._value:
            self._value = value
            ready = [
                self._events.pop(key)
                for key in list(self._events.keys())
                if key <= self._value
            ]
            for event in ready:
                event.set()
        elif value < self._value:
            raise ValueError("You cannot decrease the value.")

    @property
    def _name(self) -> str:
        return self.__name.decode("utf-8")

    async def _debug_daemon(self) -> None:
        """
        Periodically logs debug information about the counter state and waiters.

        This method is used internally to provide debugging information when debug logging is enabled.
        """
        cdef time_t start, now 
        start = time(NULL)
        while self._events:
            now = time(NULL)
            self.get_logger().debug(
                "%s is still locked after %sm", self, round(now - start / 60, 2)
            )
            await asyncio.sleep(300)

    def __dealloc__(self):
        # Free the memory allocated for __name
        if self.__name is not NULL:
            free(self.__name)


class CounterLockCluster:
    """
    An asyncio primitive that represents a collection of :class:`CounterLock` objects.

    `wait_for(i)` will wait until the value of all :class:`CounterLock` objects is >= i.

    See Also:
        :class:`CounterLock` for managing individual counters.
    """

    __slots__ = ("locks",)

    def __init__(self, counter_locks: Iterable[CounterLock]) -> None:
        """
        Initializes the :class:`CounterLockCluster` with a collection of :class:`CounterLock` objects.

        Args:
            counter_locks: The :class:`CounterLock` objects to manage.

        Examples:
            >>> lock1 = CounterLock(start_value=0)
            >>> lock2 = CounterLock(start_value=0)
            >>> cluster = CounterLockCluster([lock1, lock2])
        """
        self.locks = list(counter_locks)

    async def wait_for(self, value: int) -> bool:
        """
        Waits until the value of all :class:`CounterLock` objects in the cluster reaches or exceeds the specified value.

        Args:
            value: The value to wait for.

        Examples:
            >>> lock1 = CounterLock(start_value=0)
            >>> lock2 = CounterLock(start_value=0)
            >>> cluster = CounterLockCluster([lock1, lock2])
            >>> await cluster.wait_for(5)  # This will block until all locks have value >= 5
        """
        await asyncio.gather(
            *[counter_lock.wait_for(value) for counter_lock in self.locks]
        )
        return True