"""
This module provides priority-based semaphore implementations. These semaphores allow 
waiters to be assigned priorities, ensuring that higher priority waiters are 
processed before lower priority ones.
"""

import asyncio
from collections import deque
from heapq import heappop, heappush
from logging import DEBUG, getLogger

from a_sync._typing import *
from a_sync.primitives.locks.semaphore cimport Semaphore

logger = getLogger(__name__)

cdef object c_logger = logger


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
        self._potential_lost_waiters: List["asyncio.Future[None]"] = []
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
        super().__init__(value, name=name)

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
        await (<_AbstractPrioritySemaphoreContextManager>self.c_getitem(self._top_priority)).c_acquire()

    async def __aexit__(self, *_) -> None:
        """Exits the semaphore context, releasing it with the top priority.

        This method is part of the asynchronous context management protocol.

        Examples:
            >>> semaphore = _AbstractPrioritySemaphore(5)
            >>> async with semaphore:
            ...     await do_stuff()
        """
        (<_AbstractPrioritySemaphoreContextManager>self.c_getitem(self._top_priority)).c_release()

    async def acquire(self) -> Literal[True]:
        """Acquires the semaphore with the top priority.

        This method overrides :meth:`Semaphore.acquire` to handle priority-based logic.

        Examples:
            >>> semaphore = _AbstractPrioritySemaphore(5)
            >>> await semaphore.acquire()
        """
        return await (<_AbstractPrioritySemaphoreContextManager>self.c_getitem(self._top_priority)).c_acquire()

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
    
    cdef object c_getitem(self, object priority):
        if self._Semaphore__value is None:
            raise ValueError(self._Semaphore__value)
        
        cdef _AbstractPrioritySemaphoreContextManager context_manager

        priority = self._top_priority if priority is None else priority
        if priority not in self._context_managers:
            context_manager = self._context_manager_class(
                self, priority, name=self.name
            )
            heappush(self._Semaphore__waiters, context_manager)  # type: ignore [misc]
            self._context_managers[priority] = context_manager
        return self._context_managers[priority]

    cpdef bint locked(self):
        """Checks if the semaphore is locked.

        Returns:
            True if the semaphore cannot be acquired immediately, False otherwise.

        Examples:
            >>> semaphore = _AbstractPrioritySemaphore(5)
            >>> semaphore.locked()
        """
        return self.c_locked()
    
    cdef bint c_locked(self):
        cdef _AbstractPrioritySemaphoreContextManager cm
        cdef object w
        if self._Semaphore__value == 0:
            return True
        cdef dict[object, _AbstractPrioritySemaphoreContextManager] cms = self._context_managers
        if not cms:
            return False
        return any(
            cm._Semaphore__waiters and any(not w.cancelled() for w in cm._Semaphore__waiters)
            for cm in cms.values()
        )

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
        self._c_wake_up_next()
    
    cdef void _c_wake_up_next(self):
        cdef _AbstractPrioritySemaphoreContextManager manager
        cdef Py_ssize_t start_len, end_len
        cdef bint woke_up

        cdef bint debug_logs = c_logger.isEnabledFor(DEBUG)
        while <list>self._Semaphore__waiters:
            manager = heappop(<list>self._Semaphore__waiters)
            if len(manager) == 0:
                # There are no more waiters, get rid of the empty manager
                if debug_logs:
                    c_logger._log(
                        DEBUG,
                        "manager %s has no more waiters, popping from %s",
                        (manager._c_repr_no_parent_(), self),
                    )
                self._context_managers.pop(manager._priority)
                continue

            woke_up = False
            start_len = len(manager)

            if debug_logs:
                c_logger._log(DEBUG, "waking up next for %s", (manager._c_repr_no_parent_(), ))
                if not manager._Semaphore__waiters:
                    c_logger._log(DEBUG, "not manager._Semaphore__waiters")

            while manager._Semaphore__waiters:
                waiter = manager._Semaphore__waiters.popleft()
                self._potential_lost_waiters.remove(waiter)
                if not waiter.done():
                    waiter.set_result(None)
                    woke_up = True
                    if debug_logs:
                        c_logger._log(DEBUG, "woke up %s", (waiter, ))
                    break

            if not woke_up:
                self._context_managers.pop(manager._priority)
                continue

            end_len = len(manager)

            assert start_len > end_len, f"start {start_len} end {end_len}"

            if end_len:
                # There are still waiters, put the manager back
                heappush(<list>self._Semaphore__waiters, manager)  # type: ignore [misc]
            else:
                # There are no more waiters, get rid of the empty manager
                self._context_managers.pop(manager._priority)
            return

        # emergency procedure (hopefully temporary):
        if not debug_logs:
            while self._potential_lost_waiters:
                waiter = self._potential_lost_waiters.pop(0)
                if not waiter.done():
                    waiter.set_result(None)
                    return
            return
            
        while self._potential_lost_waiters:
            waiter = self._potential_lost_waiters.pop(0)
            c_logger._log(DEBUG, "we found a lost waiter %s", (waiter, ))
            if not waiter.done():
                waiter.set_result(None)
                c_logger._log(DEBUG, "woke up lost waiter %s", (waiter, ))
                return

        c_logger._log(DEBUG, "%s has no waiters to wake", (self, ))


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

        super().__init__(0, name=name)

        self._parent = parent
        """The parent semaphore."""

        self._priority = priority
        """The priority associated with this context manager."""

    def __repr__(self) -> str:
        """Returns a string representation of the context manager."""
        return f"<{self.__class__.__name__} parent={self._parent} {self._priority_name}={self._priority} waiters={len(self)}>"

    cpdef str _repr_no_parent_(self):
        """Returns a string representation of the context manager without the parent."""
        return self._c_repr_no_parent_()

    cdef str _c_repr_no_parent_(self):
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
    
    cdef object c_acquire(self):
        if self._parent._Semaphore__value <= 0:
            self._c_ensure_debug_daemon((),{})
        return self.__acquire()
    
    async def __acquire(self) -> Literal[True]:
        cdef object loop, fut
        while self._parent._Semaphore__value <= 0:
            if self._Semaphore__waiters is None:
                self._Semaphore__waiters = deque()
            fut = self._c_get_loop().create_future()
            self._Semaphore__waiters.append(fut)
            self._parent._potential_lost_waiters.append(fut)
            try:
                await fut
            except:
                # See the similar code in Queue.get.
                fut.cancel()
                if self._parent._Semaphore__value > 0 and not fut.cancelled():
                    self._parent._wake_up_next()
                raise
        self._parent._Semaphore__value -= 1
        return True

    cpdef void release(self):
        """Releases the semaphore for this context manager.

        This method overrides :meth:`Semaphore.release` to handle priority-based logic.

        Examples:
            >>> context_manager = _AbstractPrioritySemaphoreContextManager(parent, priority=1)
            >>> context_manager.release()
        """
        self._parent.c_release()

    cdef void c_release(self):
        """Releases the semaphore for this context manager.

        This method overrides :meth:`Semaphore.release` to handle priority-based logic.

        Examples:
            >>> context_manager = _AbstractPrioritySemaphoreContextManager(parent, priority=1)
            >>> context_manager.release()
        """
        self._parent.c_release()


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
        if other.__class__ is not self.__class__:
            raise TypeError(f"{other} is not type {self.__class__.__name__}")
        return <int>self._priority < <int>other._priority

cdef class PrioritySemaphore(_AbstractPrioritySemaphore):  # type: ignore [type-var]
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
        self._potential_lost_waiters: List["asyncio.Future[None]"] = []
        """A list of futures representing waiters that might have been lost."""
    
    def __init__(
        self, 
        value: int = 1, 
        *, 
        name: Optional[str] = None, 
    ) -> None:
        # context manager class is some temporary hacky shit, just ignore this
        super().__init__(_PrioritySemaphoreContextManager, -1, value, name=name)

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
    
    cdef object c_getitem(self, object priority):
        if self._Semaphore__value is None:
            raise ValueError(self._Semaphore__value)
        
        cdef _PrioritySemaphoreContextManager context_manager

        cdef dict[int, _PrioritySemaphoreContextManager] context_managers = self._context_managers
        if <int>priority not in context_managers:
            context_manager = _PrioritySemaphoreContextManager(self, <int>priority, name=self.name)
            heappush(
                <list[_PrioritySemaphoreContextManager]>self._Semaphore__waiters,
                context_manager,
            )  # type: ignore [misc]
            context_managers[<int>priority] = context_manager
            return context_manager
        return context_managers[<int>priority]