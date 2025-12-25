# cython: boundscheck=False
"""
This module provides priority‐based semaphore implementations. These semaphores allow
waiters to be assigned priorities, ensuring that higher priority waiters are processed
before lower priority ones.
"""

import asyncio
import collections
import heapq
from logging import getLogger
from typing import List, Literal, Optional, Protocol, Set, Type, TypeVar

from cpython.unicode cimport PyUnicode_CompareWithASCIIString

from a_sync.primitives.locks.semaphore cimport Semaphore


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

# Type variables for priority and context manager types
PT = TypeVar("PT", bound=object)
CM = TypeVar("CM", bound="_AbstractPrioritySemaphoreContextManager")


cdef class _AbstractPrioritySemaphore(Semaphore):
    """A semaphore that allows prioritization of waiters.

    This semaphore manages waiters with associated priorities, ensuring that
    waiters with higher priorities are processed before those with lower priorities.
    Subclasses must define the `_top_priority` attribute to specify the default top
    priority behavior. The attribute `_context_manager_class` should specify the class
    used for managing semaphore contexts.

    See Also:
        :class:`PrioritySemaphore` for an implementation using numeric priorities.

    Examples:
        >>> semaphore = PrioritySemaphore(5, name="test_semaphore")
        >>> async with semaphore:
        ...     # do something
        ...     pass
    """

    def __cinit__(self) -> None:
        self._context_managers = {}
        """dict: A dictionary mapping priorities to their context managers."""
    
        self._Semaphore__waiters = []
        """list: A heap queue of context managers, sorted by priority."""

        # NOTE: This should (hopefully) be temporary
        self._potential_lost_waiters = set()
        """set: A set of futures representing waiters that might have been lost."""
    
    def __init__(
        self, 
        context_manager_class: Type[_AbstractPrioritySemaphoreContextManager],
        top_priority: object,
        value: int = 1, 
        *, 
        name: Optional[str] = None, 
    ) -> None:
        """Initialize the priority semaphore.

        Args:
            context_manager_class: The class used to manage context for a given priority.
            top_priority: The default top priority value.
            value: The initial capacity of the semaphore.
            name: An optional name for the semaphore, used for debugging.

        Examples:
            >>> semaphore = PrioritySemaphore(5, name="test_semaphore")
        """
        # context manager class is some temporary hacky shit, just ignore this
        Semaphore.__init__(self, value, name=name)

        self._capacity = value
        """int: The initial capacity of the semaphore."""

        self._top_priority = top_priority
        self._top_priority_manager = context_manager_class(
                self, top_priority, name=self.name
            )
        self._context_manager_class = context_manager_class

    def __repr__(self) -> str:
        """Return a string representation of the semaphore.

        Examples:
            >>> repr(semaphore)
            '<_AbstractPrioritySemaphore name=test_semaphore capacity=5 value=3 waiters={...}>'
        """
        return f"<{self.__class__.__name__} name={self.name} capacity={self._capacity} value={self._Semaphore__value} waiters={self._count_waiters()}>"

    async def __aenter__(self) -> None:
        """Acquire the semaphore with top priority when entering an async context.

        Examples:
            >>> async with semaphore:
            ...     await do_stuff()
        """
        await self._top_priority_manager.acquire()

    async def __aexit__(self, *_) -> None:
        """Release the semaphore with top priority when exiting an async context.

        Examples:
            >>> async with semaphore:
            ...     await do_stuff()
        """
        self._top_priority_manager.release()

    cpdef object acquire(self):
        """Acquire the semaphore with top priority.

        Overrides :meth:`Semaphore.acquire` to handle priority-based logic.

        Examples:
            >>> await semaphore.acquire()
        """
        return self._top_priority_manager.acquire()

    def __getitem__(
        self, priority: Optional[PT]
    ) -> "_AbstractPrioritySemaphoreContextManager[PT]":
        """Retrieve the context manager for a given priority.

        Args:
            priority: The priority for which to retrieve the context manager.
                If None, the top priority is used.

        Returns:
            The context manager associated with the specified priority.

        Examples:
            >>> semaphore = PrioritySemaphore(5)
            >>> context_manager = semaphore[3]
            >>> async with context_manager:
            ...     await do_something()
        """
        return self.c_getitem(priority)
    
    cdef _AbstractPrioritySemaphoreContextManager c_getitem(self, object priority):
        cdef _AbstractPrioritySemaphoreContextManager context_manager
        cdef dict[object, _AbstractPrioritySemaphoreContextManager] context_managers

        if priority is None or priority == self._top_priority:
            return self._top_priority_manager
        
        context_managers = self._context_managers
        context_manager = context_managers.get(priority)
        if context_manager is None:
            context_manager = self._context_manager_class(
                self, priority, name=self.name
            )
            heappush(self._Semaphore__waiters, context_manager)
            context_managers[priority] = context_manager
        return context_manager

    cpdef bint locked(self):
        """Determine if the semaphore is locked.

        Returns:
            True if the semaphore cannot be acquired immediately, False otherwise.

        Examples:
            >>> is_locked = semaphore.locked()
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
        """Count the number of waiters for each priority.

        Returns:
            A dict mapping each priority to the count of waiters with that priority.

        Examples:
            >>> counts = semaphore._count_waiters()
        """
        cdef _AbstractPrioritySemaphoreContextManager manager
        cdef list[_AbstractPrioritySemaphoreContextManager] waiters = self._Semaphore__waiters
        return {manager._priority: len(manager._Semaphore__waiters) for manager in sorted(waiters)}
        
    cpdef void _wake_up_next(self):
        """Wake up the next waiting context manager based on priority.

        This method handles waking waiters with priority order and includes an emergency
        mechanism to handle potentially lost waiters.

        Examples:
            >>> semaphore._wake_up_next()
        """
        cdef _AbstractPrioritySemaphoreContextManager manager
        cdef object manager_waiters, get_next
        cdef Py_ssize_t start_len, end_len
        cdef set potential_lost_waiters
        cdef bint woke_up, debug_logs

        manager = self._top_priority_manager
        manager_waiters = manager._Semaphore__waiters
        potential_lost_waiters = self._potential_lost_waiters
        debug_logs = _logger_is_enabled(DEBUG)
        if manager_waiters:
            get_next = manager_waiters.popleft
            while manager_waiters:
                waiter = get_next()
                potential_lost_waiters.discard(waiter)
                if _is_not_done(waiter):
                    waiter.set_result(None)
                    if debug_logs:
                        log_debug("woke up %s", (waiter, ))
                    return
        
        while manager_waiters:
            waiter = get_next()
            potential_lost_waiters.discard(waiter)
            if _is_not_done(waiter):
                waiter.set_result(None)
                if debug_logs:
                    log_debug("woke up %s", (waiter, ))
                return

        cdef list self_waiters = self._Semaphore__waiters
        while self_waiters:
            manager = heappop(self_waiters)
            if len(manager) == 0:
                # There are no more waiters, remove the empty manager.
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

            if manager_waiters:
                get_next = manager_waiters.popleft
                waiter = get_next()
                potential_lost_waiters.discard(waiter)
                if _is_not_done(waiter):
                    waiter.set_result(None)
                    woke_up = True
                    if debug_logs:
                        log_debug("woke up %s", (waiter, ))
                    break

                if not woke_up:
                    while manager_waiters:
                        waiter = get_next()
                        potential_lost_waiters.discard(waiter)
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
                # Still waiters remain; add the manager back.
                heappush(self_waiters, manager)
            else:
                # Remove empty manager.
                self._context_managers.pop(manager._priority)
            return

        # Emergency procedure (temporary):
        if not debug_logs:
            while potential_lost_waiters:
                waiter = potential_lost_waiters.pop()
                if _is_not_done(waiter):
                    waiter.set_result(None)
                    return
            return
            
        while potential_lost_waiters:
            waiter = potential_lost_waiters.pop()
            log_debug("we found a lost waiter %s", (waiter, ))
            if _is_not_done(waiter):
                waiter.set_result(None)
                log_debug("woke up lost waiter %s", (waiter, ))
                return

        log_debug("%s has no waiters to wake", (self, ))


cdef class _AbstractPrioritySemaphoreContextManager(Semaphore):
    """Context manager for priority semaphore waiters.

    This context manager is associated with a specific priority and handles
    the acquisition and release of the semaphore for waiters with that priority.

    See Also:
        :class:`PrioritySemaphore` for an overview of numeric priority surrogates.
    """

    def __init__(
        self,
        parent: _AbstractPrioritySemaphore,
        priority: PT,
        name: Optional[str] = None,
    ) -> None:
        """Initialize the context manager for a specific priority.

        Args:
            parent: The parent semaphore.
            priority: The priority associated with this context manager.
            name: An optional name for debugging purposes.

        Examples:
            >>> parent_semaphore = PrioritySemaphore(5)
            >>> context_manager = _AbstractPrioritySemaphoreContextManager(parent_semaphore, priority=3)
        """
        Semaphore.__init__(self, 0, name=name)

        self._parent = parent
        """_AbstractPrioritySemaphore: The parent semaphore."""
        self._priority = priority
        """object: The priority associated with this context manager."""

    def __repr__(self) -> str:
        """Return a string representation of the context manager.

        Examples:
            >>> context_manager.__repr__()
            "<_AbstractPrioritySemaphoreContextManager parent_name=test_semaphore priority=3 waiters=2>"
        """
        return f"<{self.__class__.__name__} parent={self._parent} {self._priority_name}={self._priority} waiters={len(self)}>"

    cpdef str _repr_no_parent_(self):
        """Return a string representation of the context manager excluding the parent.

        Examples:
            >>> context_manager._repr_no_parent_()
            "<_AbstractPrioritySemaphoreContextManager parent_name=test_semaphore priority=3 waiters=2>"
        """
        return f"<{self.__class__.__name__} parent_name={self._parent.name} {self._priority_name}={self._priority} waiters={len(self)}>"

    def __richcmp__(self, _AbstractPrioritySemaphoreContextManager other, int op) -> bint:
        """Perform rich comparison based on priority.

        Args:
            other: Another context manager.
            op: Comparison operator (0: <, 1: <=, 2: ==, 3: !=, 4: >, 5: >=).

        Returns:
            The boolean result of the comparison.

        Examples:
            >>> cm1 = _AbstractPrioritySemaphoreContextManager(parent, priority=1)
            >>> cm2 = _AbstractPrioritySemaphoreContextManager(parent, priority=2)
            >>> cm1 < cm2
        """
        if op == 0:  # Py_LT
            return self._priority < other._priority
        elif op == 1:  # Py_LE
            return self._priority <= other._priority
        elif op == 2:  # Py_EQ
            return self is other
        elif op == 3:  # Py_NE
            return self is not other
        elif op == 4:  # Py_GT
            return self._priority > other._priority
        elif op == 5:  # Py_GE
            return self._priority >= other._priority
        return NotImplemented

    cpdef object acquire(self):
        """Acquire the semaphore for this priority context.

        If the internal counter is positive, it is decremented by one and returns immediately.
        Otherwise, it blocks until another coroutine calls release().

        Examples:
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
            parent._potential_lost_waiters.add(fut)
            try:
                await fut
            except:
                fut.cancel()
                if parent._Semaphore__value > 0 and _is_not_cancelled(fut):
                    parent._wake_up_next()
                raise
        parent._Semaphore__value -= 1
        return True

    cpdef void release(self):
        """Release the semaphore for this priority context.

        This calls the parent's release() method to update the semaphore state.

        Examples:
            >>> context_manager.release()
        """
        self._parent.release()


cdef class _PrioritySemaphoreContextManager(_AbstractPrioritySemaphoreContextManager):
    """Context manager for numeric priority semaphores."""

    def __cinit__(self):
        self._priority_name = "priority"
        self._Semaphore__waiters = deque()
        self._decorated: Set[str] = set()

    def __richcmp__(self, _PrioritySemaphoreContextManager other, int op) -> bint:
        """Perform rich comparison for numeric priority context managers.

        Args:
            other: Another priority context manager.
            op: Comparison operator (0: <, 1: <=, 2: ==, 3: !=, 4: >, 5: >=).

        Returns:
            The boolean result of the comparison based on numeric priority.

        Examples:
            >>> cm1 = _PrioritySemaphoreContextManager(parent, 1)
            >>> cm2 = _PrioritySemaphoreContextManager(parent, 2)
            >>> cm1 < cm2
        """
        if op == 0:  # Py_LT
            return <int>self._priority < <int>other._priority
        elif op == 1:  # Py_LE
            return <int>self._priority <= <int>other._priority
        elif op == 2:  # Py_EQ
            return self is other
        elif op == 3:  # Py_NE
            return self is not other
        elif op == 4:  # Py_GT
            return <int>self._priority > <int>other._priority
        elif op == 5:  # Py_GE
            return <int>self._priority >= <int>other._priority
        return NotImplemented

cdef class PrioritySemaphore(_AbstractPrioritySemaphore):
    """Semaphore that uses numeric priorities for waiters.

    This class extends :class:`_AbstractPrioritySemaphore` and provides a concrete
    implementation using numeric priorities. The `_context_manager_class` is set to
    :class:`_PrioritySemaphoreContextManager`, and the `_top_priority` is set to -1,
    which is considered the highest (default) priority.

    Examples:
        Using numeric priorities with the semaphore:
        >>> priority_semaphore = PrioritySemaphore(10)
        >>> async with priority_semaphore[3]:
        ...     await do_something()

        Using top priority (default) when no specific priority is provided:
        >>> async with priority_semaphore:
        ...     await do_something()

    See Also:
        :class:`_AbstractPrioritySemaphore` for the base priority semaphore implementation.
    """

    def __cinit__(self):        
        self._context_managers = {}
        """dict: Maps numeric priorities to their context managers."""
    
        self._Semaphore__waiters = []
        """list: A heap queue of context managers, sorted by numeric priority."""

        # NOTE: This should (hopefully) be temporary
        self._potential_lost_waiters = set()
        """set: A set of futures representing waiters that might have been lost."""
    
    def __init__(
        self, 
        value: int = 1, 
        *, 
        name: Optional[str] = None, 
    ) -> None:
        _AbstractPrioritySemaphore.__init__(self, _PrioritySemaphoreContextManager, -1, value, name=name)

    def __getitem__(
        self, priority: Optional[PT]
    ) -> "_PrioritySemaphoreContextManager[PT]":
        """Retrieve the numeric priority context manager for a given priority.

        Args:
            priority: The numeric priority to retrieve. If None, the top priority (-1) is used.

        Returns:
            The numeric priority context manager associated with the given priority.

        Examples:
            >>> semaphore = PrioritySemaphore(5)
            >>> context_manager = semaphore[3]
            >>> async with context_manager:
            ...     await do_something()
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