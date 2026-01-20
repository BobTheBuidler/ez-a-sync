import asyncio
import functools
from logging import Logger
from threading import Thread
from types import TracebackType
from typing import Any, DefaultDict, Literal, override

from typing_extensions import Never

from a_sync._typing import CoroFn, P, T
from a_sync.primitives._debug import _DebugDaemonMixin

logger: Logger

async def _noop() -> Literal[True]: ...

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

    name: str
    """An optional name for the counter, used in debug logs. Defaults to an empty string."""

    def __init__(
        self,
        value: int = 1,
        name: str = "",
        loop: asyncio.AbstractEventLoop | None = ...,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the semaphore with a given value and optional name for debugging.

        Args:
            value: The initial value for the semaphore.
            name (optional): An optional name used only to provide useful context in debug logs.
        """

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

    def __len__(self) -> int: ...
    def decorate(self, fn: CoroFn[P, T]) -> CoroFn[P, T]:
        """
        Wrap a coroutine function to ensure it runs with the semaphore.

        Example:
            semaphore = Semaphore(5)

            @semaphore
            async def limited():
                return 1
        """

    @override
    async def acquire(self) -> Literal[True]:
        """
        Acquire the semaphore, ensuring that debug logging is enabled if there are waiters.

        If the semaphore value is zero or less, the debug daemon is started to log the state of the semaphore.

        Returns:
            True when the semaphore is successfully acquired.
        """

    @override
    async def _debug_daemon(
        self,
        fut: asyncio.Future[Any],
        fn: Any,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Daemon coroutine (runs in a background task) which will emit a debug log every minute while the semaphore has waiters.

        This method is part of the :class:`_DebugDaemonMixin` and is used to provide detailed logging information
        about the semaphore's state when it is being waited on.

        This code will only run if `self.logger.isEnabledFor(logging.DEBUG)` is True. You do not need to include any level checks in your custom implementations.

        Example:
            semaphore = Semaphore(5)

            async def monitor():
                await semaphore._debug_daemon()
        """

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

    name: str
    def __init__(self, name: str | None = None) -> None:
        """
        Initialize the dummy semaphore with an optional name.

        Args:
            name (optional): An optional name for the dummy semaphore.
        """

    @override
    async def acquire(self) -> Literal[True]:
        """Acquire the dummy semaphore, which is a no-op."""

    @override
    def release(self) -> None:
        """No-op release method."""

    @override
    async def __aenter__(self) -> None:
        """No-op context manager entry."""

    @override
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
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

    semaphores: DefaultDict[Thread, Semaphore] | dict[Never, Never]
    dummy: DummySemaphore | None
    def __init__(self, value: int | None, name: str | None = None) -> None:
        """
        Initialize the threadsafe semaphore with a given value and optional name.

        Args:
            value: The initial value for the semaphore, should be an integer.
            name (optional): An optional name for the semaphore.
        """

    @override
    def __len__(self) -> int: ...
    @functools.cached_property
    def use_dummy(self) -> bool:
        """
        Determine whether to use a dummy semaphore.

        Returns:
            True if the semaphore value is None, indicating the use of a dummy semaphore.
        """

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

    @override
    async def __aenter__(self) -> None: ...
    @override
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...
