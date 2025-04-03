# cython: boundscheck=False
"""
This module provides priority-based semaphore implementations. These semaphores allow 
waiters to be assigned priorities, ensuring that higher priority waiters are 
processed before lower priority ones.
"""

import asyncio
import collections
import heapq
from logging import getLogger
from typing import List, Literal, Optional, Protocol, Set, Type, TypeVar

from a_sync.primitives.locks.semaphore cimport Semaphore

# cdef asyncio
cdef object Future = asyncio.Future
del asyncio

# cdef collections
cdef object deque = collections.deque
del collections

# cdef heapq
cdef object heappush = heapq.heappush
cdef object heappop = heapq.heappop
del heapq

# cdef logging
cdef public object logger = getLogger(__name__)
cdef object c_logger = logger
cdef object DEBUG = 10
cdef object _logger_log = logger._log
cdef object _logger_is_enabled = logger.isEnabledFor
del getLogger

class Priority(Protocol):
    def __lt__(self, other) -> bool: ...


PT = TypeVar("PT", bound=Priority)

CM = TypeVar("CM", bound="_AbstractPrioritySemaphoreContextManager[Priority]")


cdef class _AbstractPrioritySemaphore(Semaphore):
    """
    A semaphore that allows prioritization of waiters.

    This semaphore manages waiters with associated priorities, ensuring that waiters with higher
    priorities are processed before those with lower priorities. Subclasses must define the
    `_top_priority` attribute to specify the default top priority behavior.

    The `_context_manager_class` attribute should specify the class used for managing semaphore contexts.

    See Also:
        :class:`PrioritySemaphore` for an implementation using numeric priorities.
    """

    def __cinit__(self) -> None:
        self._context_managers = {}
        """A dictionary mapping priorities to their context managers."""
    
        self._Semaphore__waiters = []
        """A heap queue of context managers, sorted by priority."""

        # NOTE: This should (hopefully) be temporary
        self._potential_lost_waiters: List["Future[None]"] = []
        """A list of futures representing waiters that might have been lost."""
    
    def __init__(
        self, 
        context_manager_class: Type[_AbstractPrioritySemaphoreContextManager],
        top_priority: object,
        value: int = 1, 
        *, 
        name: Optional[str] = None, 
    ) -> None:
        """Initializes the priority semaphore.

        Args:
            value: The initial capacity of the semaphore.
            name: An optional name for the semaphore, used for debugging.

        Examples:
            >>> semaphore = _AbstractPrioritySemaphore(5, name="test_semaphore")
        """
        # context manager class is some temporary hacky shit, just ignore this
        Semaphore.__init__(self, value, name=name)

        self._capacity = value
        """The initial capacity of the semaphore."""

        self._top_priority = top_priority
        self._context_manager_class = context_manager_class

    def __repr__(self) -> str:
        """Returns a string representation of the semaphore."""
        return f"<{self.__class__.__name__} name={self.name} capacity={self._capacity} value={self._Semaphore__value} waiters={self._count_waiters()}>"

    async def __aenter__(self) -> None:
        """Enters the semaphore context, acquiring it with the top priority.

        This method is part of the asynchronous context management protocol.

        Examples:
            >>> semaphore = _AbstractPrioritySemaphore(5)
            >>> async with semaphore:
            ...     await do_stuff()
        """
        await self.c_getitem(self._top_priority).acquire()

    async def __aexit__(self, *_) -> None:
        """Exits the semaphore context, releasing it with the top priority.

        This method is part of the asynchronous context management protocol.

        Examples:
            >>> semaphore = _AbstractPrioritySemaphore(5)
            >>> async with semaphore:
            ...     await do_stuff()
        """
        self.c_getitem(self._top_priority).release()

    cpdef object acquire(self):
        """Acquires the semaphore with the top priority.

        This method overrides :meth:`Semaphore.acquire` to handle priority-based logic.

        Examples:
            >>> semaphore = _AbstractPrioritySemaphore(5)
            >>> await semaphore.acquire()
        """
        return self.c_getitem(self._top_priority).acquire()

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
        return self.c_getitem(priority)
    
    cdef _AbstractPrioritySemaphoreContextManager c_getitem(self, object priority):
        cdef _AbstractPrioritySemaphoreContextManager context_manager
        cdef dict[object, _AbstractPrioritySemaphoreContextManager] context_managers

        context_managers = self._context_managers
        priority = self._top_priority if priority is None else priority
        context_manager = context_managers.get(priority)
        if context_manager is None:
            context_manager = self._context_manager_class(
                self, priority, name=self.name
            )
            heappush(self._Semaphore__waiters, context_manager)
            context_managers[priority] = context_manager
        return context_manager

    cpdef bint locked(self):
        """Checks if the semaphore is locked.

        Returns:
            True if the semaphore cannot be acquired immediately, False otherwise.

        Examples:
            >>> semaphore = _AbstractPrioritySemaphore(5)
            >>> semaphore.locked()
        """
        cdef list waiters
        if self._Semaphore__value == 0:
            return True
        for cm in self._context_managers.values():
            waiters = (<Semaphore>cm).__waiters
            for waiter in waiters:
                if _is_not_cancelled(waiter):
                    return True
        return False

    cdef dict[object, Py_ssize_t] _count_waiters(self):
        """Counts the number of waiters for each priority.

        Returns:
            A dictionary mapping each priority to the number of waiters.

        Examples:
            >>> semaphore = _AbstractPrioritySemaphore(5)
            >>> semaphore._count_waiters()
        """
        cdef _AbstractPrioritySemaphoreContextManager manager
        cdef list[_AbstractPrioritySemaphoreContextManager] waiters = self._Semaphore__waiters
        return {manager._priority: len(manager._Semaphore__waiters) for manager in sorted(waiters)}
        
    cpdef void _wake_up_next(self):
        """Wakes up the next waiter in line.

        This method handles the waking of waiters based on priority. It includes an emergency
        procedure to handle potential lost waiters, ensuring that no waiter is left indefinitely
        waiting.

        The emergency procedure is a temporary measure to address potential issues with lost waiters.

        Examples:
            >>> semaphore = _AbstractPrioritySemaphore(5)
            >>> semaphore._wake_up_next()
        """
        cdef _AbstractPrioritySemaphoreContextManager manager
        cdef Py_ssize_t start_len, end_len
        cdef bint woke_up

        cdef list self_waiters = self._Semaphore__waiters
        cdef list potential_lost_waiters = self._potential_lost_waiters
        cdef bint debug_logs = _logger_is_enabled(DEBUG)
        while self_waiters:
            manager = heappop(self_waiters)
            if len(manager) == 0:
                # There are no more waiters, get rid of the empty manager
                if debug_logs:
                    log_debug(
                        "manager %s has no more waiters, popping from %s",
                        (manager._repr_no_parent_(), self),
                    )
                self._context_managers.pop(manager._priority)
                continue

            woke_up = False
            start_len = len(manager)

            manager_waiters = manager._Semaphore__waiters
            if debug_logs:
                log_debug("waking up next for %s", (manager._repr_no_parent_(), ))
                if not manager_waiters:
                    log_debug("not manager._Semaphore__waiters", ())

            while manager_waiters:
                waiter = manager_waiters.popleft()
                potential_lost_waiters.remove(waiter)
                if _is_not_done(waiter):
                    waiter.set_result(None)
                    woke_up = True
                    if debug_logs:
                        log_debug("woke up %s", (waiter, ))
                    break

            if not woke_up:
                self._context_managers.pop(manager._priority)
                continue

            end_len = len(manager)

            assert start_len > end_len, f"start {start_len} end {end_len}"

            if end_len:
                # There are still waiters, put the manager back
                heappush(self_waiters, manager)
            else:
                # There are no more waiters, get rid of the empty manager
                self._context_managers.pop(manager._priority)
            return

        # emergency procedure (hopefully temporary):
        if not debug_logs:
            while potential_lost_waiters:
                waiter = potential_lost_waiters.pop(0)
                if _is_not_done(waiter):
                    waiter.set_result(None)
                    return
            return
            
        while potential_lost_waiters:
            waiter = potential_lost_waiters.pop(0)
            log_debug("we found a lost waiter %s", (waiter, ))
            if _is_not_done(waiter):
                waiter.set_result(None)
                log_debug("woke up lost waiter %s", (waiter, ))
                return

        log_debug("%s has no waiters to wake", (self, ))


cdef class _AbstractPrioritySemaphoreContextManager(Semaphore):
    """
    A context manager for priority semaphore waiters.

    This context manager is associated with a specific priority and handles
    the acquisition and release of the semaphore for waiters with that priority.
    """

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

        Semaphore.__init__(self, 0, name=name)

        self._parent = parent
        """The parent semaphore."""

        self._priority = priority
        """The priority associated with this context manager."""

    def __repr__(self) -> str:
        """Returns a string representation of the context manager."""
        return f"<{self.__class__.__name__} parent={self._parent} {self._priority_name}={self._priority} waiters={len(self)}>"

    cpdef str _repr_no_parent_(self):
        """Returns a string representation of the context manager without the parent."""
        return f"<{self.__class__.__name__} parent_name={self._parent.name} {self._priority_name}={self._priority} waiters={len(self)}>"

    def __lt__(self, _AbstractPrioritySemaphoreContextManager other) -> bool:
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
        return self._priority < other._priority

    cpdef object acquire(self):
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
        if self._parent._Semaphore__value <= 0:
            self._c_ensure_debug_daemon((),{})
        return self.__acquire()
    
    async def __acquire(self) -> Literal[True]:
        cdef object fut
        cdef _AbstractPrioritySemaphore parent = self._parent
        while parent._Semaphore__value <= 0:
            if self._Semaphore__waiters is None:
                self._Semaphore__waiters = deque()
            fut = self._c_get_loop().create_future()
            self._Semaphore__waiters.append(fut)
            parent._potential_lost_waiters.append(fut)
            try:
                await fut
            except:
                # See the similar code in Queue.get.
                fut.cancel()
                if parent._Semaphore__value > 0 and _is_not_cancelled(fut):
                    parent._wake_up_next()
                raise
        parent._Semaphore__value -= 1
        return True

    cpdef void release(self):
        """Releases the semaphore for this context manager.

        This method overrides :meth:`Semaphore.release` to handle priority-based logic.

        Examples:
            >>> context_manager = _AbstractPrioritySemaphoreContextManager(parent, priority=1)
            >>> context_manager.release()
        """
        self._parent.release()


cdef inline bint _is_not_done(fut: Future):
    return <str>fut._state == "PENDING"

cdef inline bint _is_not_cancelled(fut: Future):
    return <str>fut._state != "CANCELLED"


cdef class _PrioritySemaphoreContextManager(_AbstractPrioritySemaphoreContextManager):
    """Context manager for numeric priority semaphores."""

    def __cinit__(self):
        self._priority_name = "priority"
        # Semaphore.__cinit__(self)
        self._Semaphore__waiters = deque()
        self._decorated: Set[str] = set()

    def __lt__(self, _PrioritySemaphoreContextManager other) -> bool:
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
        return <int>self._priority < <int>other._priority

cdef class PrioritySemaphore(_AbstractPrioritySemaphore):
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

    def __cinit__(self):        
        # _AbstractPrioritySemaphore.__cinit__(self)

        self._context_managers = {}
        """A dictionary mapping priorities to their context managers."""
    
        self._Semaphore__waiters = []
        """A heap queue of context managers, sorted by priority."""

        # NOTE: This should (hopefully) be temporary
        self._potential_lost_waiters: List["Future[None]"] = []
        """A list of futures representing waiters that might have been lost."""
    
    def __init__(
        self, 
        value: int = 1, 
        *, 
        name: Optional[str] = None, 
    ) -> None:
        # context manager class is some temporary hacky shit, just ignore this
        _AbstractPrioritySemaphore.__init__(self, _PrioritySemaphoreContextManager, -1, value, name=name)

    def __getitem__(
        self, priority: Optional[PT]
    ) -> "_PrioritySemaphoreContextManager[PT]":
        """Gets the context manager for a given priority.

        Args:
            priority: The priority for which to get the context manager. If None, uses the top priority.

        Returns:
            The context manager associated with the given priority.

        Examples:
            >>> semaphore = _AbstractPrioritySemaphore(5)
            >>> context_manager = semaphore[priority]
        """
        return self.c_getitem(priority or -1)
    
    cdef _PrioritySemaphoreContextManager c_getitem(self, object priority):
        if self._Semaphore__value is None:
            raise ValueError(self._Semaphore__value)
        
        cdef dict[int, _PrioritySemaphoreContextManager] context_managers
        cdef _PrioritySemaphoreContextManager context_manager
        
        context_managers = self._context_managers
        context_manager = context_managers.get(priority)
        if context_manager is None:
            context_manager = _PrioritySemaphoreContextManager(self, <int>priority, name=self.name)
            heappush(self._Semaphore__waiters, context_manager)
            context_managers[<int>priority] = context_manager
        return context_manager
    

cdef void log_debug(str message, tuple args):
    _logger_log(DEBUG, message, args)
