"""
This module provides various semaphore implementations, including a debug-enabled semaphore,
a dummy semaphore that does nothing, and a threadsafe semaphore for use in multi-threaded applications.
"""

import asyncio
import functools
import logging
import sys
from collections import defaultdict
from threading import Thread, current_thread

from a_sync._typing import *
from a_sync.primitives._debug import _DebugDaemonMixin

logger = logging.getLogger(__name__)


class Semaphore(asyncio.Semaphore, _DebugDaemonMixin):
    """
    A semaphore with additional debugging capabilities inherited from :class:`_DebugDaemonMixin`.

    This semaphore includes debug logging capabilities that are activated when the semaphore has waiters.
    It allows rewriting the pattern of acquiring a semaphore within a coroutine using a decorator.

    Example:
        You can write this pattern:

        ```
        semaphore = Semaphore(5)

        async def limited():
            async with semaphore:
                return 1
        ```

        like this:

        ```
        semaphore = Semaphore(5)

        @semaphore
        async def limited():
            return 1
        ```

    See Also:
        :class:`_DebugDaemonMixin` for more details on debugging capabilities.
    """

    if sys.version_info >= (3, 10):
        __slots__ = "name", "_value", "_waiters", "_decorated"
    else:
        __slots__ = "name", "_value", "_waiters", "_loop", "_decorated"

    def __init__(self, value: int, name=None, **kwargs) -> None:
        """
        Initialize the semaphore with a given value and optional name for debugging.

        Args:
            value: The initial value for the semaphore.
            name (optional): An optional name used only to provide useful context in debug logs.
        """
        super().__init__(value, **kwargs)
        self.name = name or self.__origin__ if hasattr(self, "__origin__") else None
        self._decorated: Set[str] = set()

    def __call__(self, fn: CoroFn[P, T]) -> CoroFn[P, T]:
        """
        Decorator method to wrap coroutine functions with the semaphore.

        This allows rewriting the pattern of acquiring a semaphore within a coroutine using a decorator.

        Example:
            semaphore = Semaphore(5)

            @semaphore
            async def limited():
                return 1
        """
        return self.decorate(fn)  # type: ignore [arg-type, return-value]

    def __repr__(self) -> str:
        representation = f"<{self.__class__.__name__} name={self.name} value={self._value} waiters={len(self)}>"
        if self._decorated:
            representation = f"{representation[:-1]} decorates={self._decorated}"
        return representation

    def __len__(self) -> int:
        return len(self._waiters) if self._waiters else 0

    def decorate(self, fn: CoroFn[P, T]) -> CoroFn[P, T]:
        """
        Wrap a coroutine function to ensure it runs with the semaphore.

        Example:
            semaphore = Semaphore(5)

            @semaphore
            async def limited():
                return 1
        """
        if not asyncio.iscoroutinefunction(fn):
            raise TypeError(f"{fn} must be a coroutine function")

        @functools.wraps(fn)
        async def semaphore_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            async with self:
                return await fn(*args, **kwargs)

        self._decorated.add(f"{fn.__module__}.{fn.__name__}")
        return semaphore_wrapper

    async def acquire(self) -> Literal[True]:
        """
        Acquire the semaphore, ensuring that debug logging is enabled if there are waiters.

        If the semaphore value is zero or less, the debug daemon is started to log the state of the semaphore.

        Returns:
            True when the semaphore is successfully acquired.
        """
        if self._value <= 0:
            self._ensure_debug_daemon()
        return await super().acquire()

    async def _debug_daemon(self) -> None:
        """
        Daemon coroutine (runs in a background task) which will emit a debug log every minute while the semaphore has waiters.

        This method is part of the :class:`_DebugDaemonMixin` and is used to provide detailed logging information
        about the semaphore's state when it is being waited on.

        Example:
            semaphore = Semaphore(5)

            async def monitor():
                await semaphore._debug_daemon()
        """
        while self._waiters:
            await asyncio.sleep(60)
            self.logger.debug(
                "%s has %s waiters for any of: %s",
                self,
                len(self),
                self._decorated,
            )


class DummySemaphore(asyncio.Semaphore):
    """
    A dummy semaphore that implements the standard :class:`asyncio.Semaphore` API but does nothing.

    This class is useful for scenarios where a semaphore interface is required but no actual synchronization is needed.

    Example:
        dummy_semaphore = DummySemaphore()

        async def no_op():
            async with dummy_semaphore:
                return 1
    """

    __slots__ = "name", "_value"

    def __init__(self, name: Optional[str] = None):
        """
        Initialize the dummy semaphore with an optional name.

        Args:
            name (optional): An optional name for the dummy semaphore.
        """
        self.name = name
        self._value = 0

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name}>"

    async def acquire(self) -> Literal[True]:
        """Acquire the dummy semaphore, which is a no-op."""
        return True

    def release(self) -> None:
        """No-op release method."""

    async def __aenter__(self):
        """No-op context manager entry."""
        return self

    async def __aexit__(self, *args):
        """No-op context manager exit."""


class ThreadsafeSemaphore(Semaphore):
    """
    A semaphore that works in a multi-threaded environment.

    This semaphore ensures that the program functions correctly even when used with multiple event loops.
    It provides a workaround for edge cases involving multiple threads and event loops by using a separate semaphore
    for each thread.

    Example:
        semaphore = ThreadsafeSemaphore(5)

        async def limited():
            async with semaphore:
                return 1

    See Also:
        :class:`Semaphore` for the base class implementation.
    """

    __slots__ = "semaphores", "dummy"

    def __init__(self, value: Optional[int], name: Optional[str] = None) -> None:
        """
        Initialize the threadsafe semaphore with a given value and optional name.

        Args:
            value: The initial value for the semaphore, should be an integer.
            name (optional): An optional name for the semaphore.
        """
        assert isinstance(value, int), f"{value} should be an integer."
        super().__init__(value, name=name)
        self.semaphores: DefaultDict[Thread, Semaphore] = defaultdict(lambda: Semaphore(value, name=self.name))  # type: ignore [arg-type]
        self.dummy = DummySemaphore(name=name)

    def __len__(self) -> int:
        return sum(len(sem._waiters) for sem in self.semaphores.values())

    @functools.cached_property
    def use_dummy(self) -> bool:
        """
        Determine whether to use a dummy semaphore.

        Returns:
            True if the semaphore value is None, indicating the use of a dummy semaphore.
        """
        return self._value is None

    @property
    def semaphore(self) -> Semaphore:
        """
        Returns the appropriate semaphore for the current thread.

        NOTE: We can't cache this property because we need to check the current thread every time we access it.

        Example:
            semaphore = ThreadsafeSemaphore(5)

            async def limited():
                async with semaphore.semaphore:
                    return 1
        """
        return self.dummy if self.use_dummy else self.semaphores[current_thread()]

    async def __aenter__(self):
        await self.semaphore.acquire()

    async def __aexit__(self, *args):
        self.semaphore.release()
