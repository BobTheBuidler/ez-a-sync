from a_sync._typing import *
import asyncio
from _typeshed import Incomplete
from a_sync.primitives.locks.semaphore import Semaphore as Semaphore
from functools import cached_property as cached_property
from typing import Protocol, TypeVar

logger: Incomplete

class Priority(Protocol):
    def __lt__(self, other) -> bool: ...

PT = TypeVar("PT", bound=Priority)
CM = TypeVar("CM", bound="_AbstractPrioritySemaphoreContextManager[Priority]")

class Comparable(Protocol):
    """Protocol for annotating comparable types."""

    def __lt__(self: CT, other: CT) -> bool: ...

CT = TypeVar("CT", bound=Comparable)

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

    def __init__(
        self,
        context_manager_class: Type[_AbstractPrioritySemaphoreContextManager],
        top_priority: Comparable,
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

    async def __aenter__(self) -> None:
        """Enters the semaphore context, acquiring it with the top priority.

        This method is part of the asynchronous context management protocol.

        Examples:
            >>> semaphore = _AbstractPrioritySemaphore(5)
            >>> async with semaphore:
            ...     await do_stuff()
        """

    async def __aexit__(self, *_) -> None:
        """Exits the semaphore context, releasing it with the top priority.

        This method is part of the asynchronous context management protocol.

        Examples:
            >>> semaphore = _AbstractPrioritySemaphore(5)
            >>> async with semaphore:
            ...     await do_stuff()
        """

    def acquire(self) -> Coroutine[Any, Any, Literal[True]]:
        """Acquires the semaphore with the top priority.

        This method overrides :meth:`Semaphore.acquire` to handle priority-based logic.

        Examples:
            >>> semaphore = _AbstractPrioritySemaphore(5)
            >>> await semaphore.acquire()
        """

    def __getitem__(self, priority: Optional[PT]) -> _AbstractPrioritySemaphoreContextManager[PT]:
        """Gets the context manager for a given priority.

        Args:
            priority: The priority for which to get the context manager. If None, uses the top priority.

        Returns:
            The context manager associated with the given priority.

        Examples:
            >>> semaphore = _AbstractPrioritySemaphore(5)
            >>> context_manager = semaphore[priority]
        """

    def locked(self) -> bool:
        """Checks if the semaphore is locked.

        Returns:
            True if the semaphore cannot be acquired immediately, False otherwise.

        Examples:
            >>> semaphore = _AbstractPrioritySemaphore(5)
            >>> semaphore.locked()
        """

class _AbstractPrioritySemaphoreContextManager(Semaphore, Generic[PT]):
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

    @cached_property
    def loop(self) -> asyncio.AbstractEventLoop:
        """Gets the event loop associated with this context manager."""

    @property
    def waiters(self) -> Deque[asyncio.Future]:
        """Gets the deque of waiters for this context manager."""

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

    def release(self) -> None:
        """Releases the semaphore for this context manager.

        This method overrides :meth:`Semaphore.release` to handle priority-based logic.

        Examples:
            >>> context_manager = _AbstractPrioritySemaphoreContextManager(parent, priority=1)
            >>> context_manager.release()
        """

class _PrioritySemaphoreContextManager(_AbstractPrioritySemaphoreContextManager[Numeric]):
    """Context manager for numeric priority semaphores."""

class PrioritySemaphore(_AbstractPrioritySemaphore[Numeric, _PrioritySemaphoreContextManager]):
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
