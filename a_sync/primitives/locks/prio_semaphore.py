"""
This module provides priority-based semaphore implementations. These semaphores allow 
waiters to be assigned priorities, ensuring that higher priority waiters are 
processed before lower priority ones.
"""

import asyncio
import heapq
import logging
from collections import deque
from functools import cached_property

from a_sync._typing import *
from a_sync.primitives.locks.semaphore import Semaphore

logger = logging.getLogger(__name__)


class Priority(Protocol):
    def __lt__(self, other) -> bool: ...


PT = TypeVar("PT", bound=Priority)

CM = TypeVar("CM", bound="_AbstractPrioritySemaphoreContextManager[Priority]")


class _AbstractPrioritySemaphore(Semaphore, Generic[PT, CM]):
    """
    A semaphore that allows prioritization of waiters.

    This semaphore manages waiters with associated priorities, ensuring that waiters with higher
    priorities are processed before those with lower priorities. Subclasses must define the
    `_top_priority` attribute to specify the default top priority behavior.

    The `_context_manager_class` attribute should specify the class used for managing semaphore contexts.

    See Also:
        :class:`PrioritySemaphore` for an implementation using numeric priorities.
    """

    name: Optional[str]
    _value: int
    _waiters: List["_AbstractPrioritySemaphoreContextManager[PT]"]  # type: ignore [assignment]
    _context_managers: Dict[PT, "_AbstractPrioritySemaphoreContextManager[PT]"]
    __slots__ = (
        "name",
        "_value",
        "_waiters",
        "_context_managers",
        "_capacity",
        "_potential_lost_waiters",
    )

    @property
    def _context_manager_class(
        self,
    ) -> Type["_AbstractPrioritySemaphoreContextManager[PT]"]:
        raise NotImplementedError

    @property
    def _top_priority(self) -> PT:
        """Defines the top priority for the semaphore.

        Subclasses must implement this property to specify the default top priority.

        Raises:
            NotImplementedError: If not implemented in a subclass.
        """
        raise NotImplementedError

    def __init__(self, value: int = 1, *, name: Optional[str] = None) -> None:
        """Initializes the priority semaphore.

        Args:
            value: The initial capacity of the semaphore.
            name: An optional name for the semaphore, used for debugging.

        Examples:
            >>> semaphore = _AbstractPrioritySemaphore(5, name="test_semaphore")
        """

        self._context_managers = {}
        """A dictionary mapping priorities to their context managers."""

        self._capacity = value
        """The initial capacity of the semaphore."""

        super().__init__(value, name=name)
        self._waiters = []
        """A heap queue of context managers, sorted by priority."""

        # NOTE: This should (hopefully) be temporary
        self._potential_lost_waiters: List["asyncio.Future[None]"] = []
        """A list of futures representing waiters that might have been lost."""

    def __repr__(self) -> str:
        """Returns a string representation of the semaphore."""
        return f"<{self.__class__.__name__} name={self.name} capacity={self._capacity} value={self._value} waiters={self._count_waiters()}>"

    async def __aenter__(self) -> None:
        """Enters the semaphore context, acquiring it with the top priority.

        This method is part of the asynchronous context management protocol.

        Examples:
            >>> semaphore = _AbstractPrioritySemaphore(5)
            >>> async with semaphore:
            ...     await do_stuff()
        """
        await self[self._top_priority].acquire()

    async def __aexit__(self, *_) -> None:
        """Exits the semaphore context, releasing it with the top priority.

        This method is part of the asynchronous context management protocol.

        Examples:
            >>> semaphore = _AbstractPrioritySemaphore(5)
            >>> async with semaphore:
            ...     await do_stuff()
        """
        self[self._top_priority].release()

    async def acquire(self) -> Literal[True]:
        """Acquires the semaphore with the top priority.

        This method overrides :meth:`Semaphore.acquire` to handle priority-based logic.

        Examples:
            >>> semaphore = _AbstractPrioritySemaphore(5)
            >>> await semaphore.acquire()
        """
        return await self[self._top_priority].acquire()

    def __getitem__(
        self, priority: Optional[PT]
    ) -> "_AbstractPrioritySemaphoreContextManager[PT]":
        """Gets the context manager for a given priority.

        Args:
            priority: The priority for which to get the context manager. If None, uses the top priority.

        Returns:
            The context manager associated with the given priority.

        Examples:
            >>> semaphore = _AbstractPrioritySemaphore(5)
            >>> context_manager = semaphore[priority]
        """
        priority = self._top_priority if priority is None else priority
        if priority not in self._context_managers:
            context_manager = self._context_manager_class(
                self, priority, name=self.name
            )
            heapq.heappush(self._waiters, context_manager)  # type: ignore [misc]
            self._context_managers[priority] = context_manager
        return self._context_managers[priority]

    def locked(self) -> bool:
        """Checks if the semaphore is locked.

        Returns:
            True if the semaphore cannot be acquired immediately, False otherwise.

        Examples:
            >>> semaphore = _AbstractPrioritySemaphore(5)
            >>> semaphore.locked()
        """
        return self._value == 0 or (
            any(
                cm._waiters and any(not w.cancelled() for w in cm._waiters)
                for cm in (self._context_managers.values() or ())
            )
        )

    def _count_waiters(self) -> Dict[PT, int]:
        """Counts the number of waiters for each priority.

        Returns:
            A dictionary mapping each priority to the number of waiters.

        Examples:
            >>> semaphore = _AbstractPrioritySemaphore(5)
            >>> semaphore._count_waiters()
        """
        return {
            manager._priority: len(manager.waiters)
            for manager in sorted(self._waiters, key=lambda m: m._priority)
        }

    def _wake_up_next(self) -> None:
        """Wakes up the next waiter in line.

        This method handles the waking of waiters based on priority. It includes an emergency
        procedure to handle potential lost waiters, ensuring that no waiter is left indefinitely
        waiting.

        The emergency procedure is a temporary measure to address potential issues with lost waiters.

        Examples:
            >>> semaphore = _AbstractPrioritySemaphore(5)
            >>> semaphore._wake_up_next()
        """
        while self._waiters:
            manager = heapq.heappop(self._waiters)
            if len(manager) == 0:
                # There are no more waiters, get rid of the empty manager
                logger.debug(
                    "manager %s has no more waiters, popping from %s",
                    manager._repr_no_parent_(),
                    self,
                )
                self._context_managers.pop(manager._priority)
                continue
            logger.debug("waking up next for %s", manager._repr_no_parent_())

            woke_up = False
            start_len = len(manager)

            if not manager._waiters:
                logger.debug("not manager._waiters")

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
            logger.debug("we found a lost waiter %s", waiter)
            if not waiter.done():
                waiter.set_result(None)
                logger.debug("woke up lost waiter %s", waiter)
                return
        logger.debug("%s has no waiters to wake", self)


class _AbstractPrioritySemaphoreContextManager(Semaphore, Generic[PT]):
    """
    A context manager for priority semaphore waiters.

    This context manager is associated with a specific priority and handles
    the acquisition and release of the semaphore for waiters with that priority.
    """

    _loop: asyncio.AbstractEventLoop
    _waiters: Deque[asyncio.Future]  # type: ignore [assignment]
    __slots__ = "_parent", "_priority"

    @property
    def _priority_name(self) -> str:
        raise NotImplementedError

    def __init__(
        self,
        parent: _AbstractPrioritySemaphore,
        priority: PT,
        name: Optional[str] = None,
    ) -> None:
        """Initializes the context manager for a specific priority.

        Args:
            parent: The parent semaphore.
            priority: The priority associated with this context manager.
            name: An optional name for the context manager, used for debugging.

        Examples:
            >>> parent_semaphore = _AbstractPrioritySemaphore(5)
            >>> context_manager = _AbstractPrioritySemaphoreContextManager(parent_semaphore, priority=1)
        """

        self._parent = parent
        """The parent semaphore."""

        self._priority = priority
        """The priority associated with this context manager."""

        super().__init__(0, name=name)

    def __repr__(self) -> str:
        """Returns a string representation of the context manager."""
        return f"<{self.__class__.__name__} parent={self._parent} {self._priority_name}={self._priority} waiters={len(self)}>"

    def _repr_no_parent_(self) -> str:
        """Returns a string representation of the context manager without the parent."""
        return f"<{self.__class__.__name__} parent_name={self._parent.name} {self._priority_name}={self._priority} waiters={len(self)}>"

    def __lt__(self, other) -> bool:
        """Compares this context manager with another based on priority.

        Args:
            other: The other context manager to compare with.

        Returns:
            True if this context manager has a lower priority than the other, False otherwise.

        Raises:
            TypeError: If the other object is not of the same type.

        Examples:
            >>> cm1 = _AbstractPrioritySemaphoreContextManager(parent, priority=1)
            >>> cm2 = _AbstractPrioritySemaphoreContextManager(parent, priority=2)
            >>> cm1 < cm2
        """
        if type(other) is not type(self):
            raise TypeError(f"{other} is not type {self.__class__.__name__}")
        return self._priority < other._priority

    @cached_property
    def loop(self) -> asyncio.AbstractEventLoop:
        """Gets the event loop associated with this context manager."""
        return self._loop or asyncio.get_event_loop()

    @property
    def waiters(self) -> Deque[asyncio.Future]:
        """Gets the deque of waiters for this context manager."""
        if self._waiters is None:
            self._waiters = deque()
        return self._waiters

    async def acquire(self) -> Literal[True]:
        """Acquires the semaphore for this context manager.

        If the internal counter is larger than zero on entry,
        decrement it by one and return True immediately. If it is
        zero on entry, block, waiting until some other coroutine has
        called release() to make it larger than 0, and then return
        True.

        This method overrides :meth:`Semaphore.acquire` to handle priority-based logic.

        Examples:
            >>> context_manager = _AbstractPrioritySemaphoreContextManager(parent, priority=1)
            >>> await context_manager.acquire()
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
        """Releases the semaphore for this context manager.

        This method overrides :meth:`Semaphore.release` to handle priority-based logic.

        Examples:
            >>> context_manager = _AbstractPrioritySemaphoreContextManager(parent, priority=1)
            >>> context_manager.release()
        """
        self._parent.release()


class _PrioritySemaphoreContextManager(
    _AbstractPrioritySemaphoreContextManager[Numeric]
):
    """Context manager for numeric priority semaphores."""

    _priority_name = "priority"


class PrioritySemaphore(_AbstractPrioritySemaphore[Numeric, _PrioritySemaphoreContextManager]):  # type: ignore [type-var]
    """Semaphore that uses numeric priorities for waiters.

    This class extends :class:`_AbstractPrioritySemaphore` and provides a concrete implementation
    using numeric priorities. The `_context_manager_class` is set to :class:`_PrioritySemaphoreContextManager`,
    and the `_top_priority` is set to -1, which is the highest priority.

    Examples:
        The primary way to use this semaphore is by specifying a priority.

        >>> priority_semaphore = PrioritySemaphore(10)
        >>> async with priority_semaphore[priority]:
        ...     await do_stuff()

        You can also enter and exit this semaphore without specifying a priority, and it will use the top priority by default:

        >>> priority_semaphore = PrioritySemaphore(10)
        >>> async with priority_semaphore:
        ...     await do_stuff()

    See Also:
        :class:`_AbstractPrioritySemaphore` for the base class implementation.
    """

    _context_manager_class = _PrioritySemaphoreContextManager
    _top_priority = -1
