from _typeshed import Incomplete
from a_sync.primitives._debug import _DebugDaemonMixin
from a_sync.primitives.locks import Event
from typing import Iterable, Optional

class CounterLock(_DebugDaemonMixin):
    """
    An async primitive that uses an internal counter to manage task synchronization.

    A coroutine can `await counter.wait_for(3)` and it will wait until the internal counter >= 3.
    If some other task executes `counter.value = 5` or `counter.set(5)`, the first coroutine will proceed as 5 >= 3.

    The internal counter can only be set to a value greater than the current value.

    See Also:
        :class:`CounterLockCluster` for managing multiple :class:`CounterLock` instances.
    """

    is_ready: Incomplete
    def __init__(self, start_value: int = 0, name: Optional[str] = None) -> None:
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

    def set(self, value: int) -> None:
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

    @property
    def value(self) -> int:
        """
        Gets the current value of the counter.

        Examples:
            >>> counter = CounterLock(start_value=0)
            >>> counter.value
            0
        """

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

    async def _debug_daemon(self) -> None:
        """
        Periodically logs debug information about the counter state and waiters.

        This method is used internally to provide debugging information when debug logging is enabled.

        This code will only run if `self.logger.isEnabledFor(logging.DEBUG)` is True. You do not need to include any level checks in your custom implementations.
        """

class CounterLockCluster:
    """
    An asyncio primitive that represents a collection of :class:`CounterLock` objects.

    `wait_for(i)` will wait until the value of all :class:`CounterLock` objects is >= i.

    See Also:
        :class:`CounterLock` for managing individual counters.
    """

    locks: Incomplete
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
