"""
This module provides various semaphore implementations, including a debug-enabled semaphore,
a dummy semaphore that does nothing, and a threadsafe semaphore for use in multi-threaded applications.
"""

import asyncio
import functools
from collections import defaultdict, deque
from threading import Thread, current_thread
from typing import Container

from a_sync._typing import *
from a_sync.primitives._debug cimport _DebugDaemonMixin


async def __acquire() -> Literal[True]:
    return True


cdef class Semaphore(_DebugDaemonMixin):
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

    def __cinit__(self) -> None:
        self.__waiters = deque()
        self._decorated: Set[str] = set()
    
    def __init__(self, value: int=1, name=None, loop=None, **kwargs) -> None:
        """
        Initialize the semaphore with a given value and optional name for debugging.

        Args:
            value: The initial value for the semaphore.
            name (optional): An optional name used only to provide useful context in debug logs.
        """
        super().__init__(loop=loop)
        if value < 0:
            raise ValueError("Semaphore initial value must be >= 0")

        try:
            self.__value = value
        except OverflowError as e:
            raise OverflowError(
                {"error": str(e), "value": value, "max value": 18446744073709551615},
                "If you need a Semaphore with a larger value, you should just use asyncio.Semaphore",
            ) from e.__cause__
            
        self._name = name or getattr(self, "__origin__", "")

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
        representation = f"<{self.__class__.__name__} name={self._name} value={self.__value} waiters={len(self)}>"
        if self._decorated:
            representation = f"{representation[:-1]} decorates={self._decorated}"
        return representation

    async def __aenter__(self):
        coro = self.c_acquire()
        await coro
        # We have no use for the "as ..."  clause in the with
        # statement for locks.
        return None

    async def __aexit__(self, exc_type, exc, tb):
        self.c_release()

    cpdef bint locked(self):
        """Returns True if semaphore cannot be acquired immediately."""
        return self.c_locked()
    
    cdef bint c_locked(self):
        """Returns True if semaphore cannot be acquired immediately."""
        if self.__value == 0:
            return True
        waiters = self.__waiters 
        if any(not w.cancelled() for w in (waiters or ())):
            return True

    def __len__(self) -> int:
        return len(self.__waiters)

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

    cpdef object acquire(self):
        """
        Acquire the semaphore, ensuring that debug logging is enabled if there are waiters.

        If the internal counter is larger than zero on entry, decrement it by one and return
        True immediately.  If it is zero on entry, block, waiting until some other coroutine 
        has called release() to make it larger than 0, and then return True.

        If the semaphore value is zero or less, the debug daemon is started to log the state of the semaphore.

        Returns:
            True when the semaphore is successfully acquired.
        """
        return self.c_acquire()
    
    cdef object c_acquire(self):
        """
        Acquire the semaphore, ensuring that debug logging is enabled if there are waiters.

        If the internal counter is larger than zero on entry, decrement it by one and return
        True immediately.  If it is zero on entry, block, waiting until some other coroutine 
        has called release() to make it larger than 0, and then return True.

        If the semaphore value is zero or less, the debug daemon is started to log the state of the semaphore.

        Returns:
            True when the semaphore is successfully acquired.
        """
        if self.__value <= 0:
            self._c_ensure_debug_daemon((),{})

        if not self.c_locked():
            self.__value -= 1
            return __acquire()

        return self.__acquire()

    async def __acquire(self) -> Literal[True]:
        # Finally block should be called before the CancelledError
        # handling as we don't want CancelledError to call
        # _wake_up_first() and attempt to wake up itself.
        
        cdef object fut = self._c_get_loop().create_future()
        self.__waiters.append(fut)
        try:
            try:
                await fut
            finally:
                self.__waiters.remove(fut)
        except asyncio.exceptions.CancelledError:
            if not fut.cancelled():
                self.__value += 1
                self._c_wake_up_next()
            raise

        if self.__value > 0:
            self._c_wake_up_next()

        return True

    cpdef void release(self):
        """Release a semaphore, incrementing the internal counter by one.

        When it was zero on entry and another coroutine is waiting for it to
        become larger than zero again, wake up that coroutine.
        """
        self.__value += 1
        self._c_wake_up_next()
    
    cdef void c_release(self):
        self.__value += 1
        self._c_wake_up_next()

    @property
    def name(self) -> str:
        return self._name

    @property
    def _value(self) -> int:
        # required for subclass compatability
        return self.__value
    
    @_value.setter
    def _value(self, unsigned long long value):
        # required for subclass compatability
        self.__value = value

    @property
    def _waiters(self) -> int:
        # required for subclass compatability
        return self.__waiters
    
    @_waiters.setter
    def _waiters(self, value: Container):
        # required for subclass compatability
        self.__waiters = value

    cpdef void _wake_up_next(self):
        """Wake up the first waiter that isn't done."""
        if not self.__waiters:
            return

        for fut in self.__waiters:
            if not fut.done():
                self.__value -= 1
                fut.set_result(True)
                return
    
    cdef void _c_wake_up_next(self):
        """Wake up the first waiter that isn't done."""
        if not self.__waiters:
            return

        for fut in self.__waiters:
            if not fut.done():
                self.__value -= 1
                fut.set_result(True)
                return
            
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
        while self.__waiters:
            await asyncio.sleep(60)
            self.get_logger().debug(
                "%s has %s waiters for any of: %s",
                self,
                len(self),
                self._decorated,
            )


cdef class DummySemaphore(Semaphore):
    """
    A dummy semaphore that implements the standard :class:`asyncio.Semaphore` API but does nothing.

    This class is useful for scenarios where a semaphore interface is required but no actual synchronization is needed.

    Example:
        dummy_semaphore = DummySemaphore()

        async def no_op():
            async with dummy_semaphore:
                return 1
    """

    def __cinit__(self):
        self.__value = 0
        self.__waiters = deque()
        self._decorated = None

    def __init__(self, name: Optional[str] = None):
        """
        Initialize the dummy semaphore with an optional name.

        Args:
            name (optional): An optional name for the dummy semaphore.
        """
        self._name = name

    def __repr__(self) -> str:
        return "<{} name={}>".format(self.__class__.__name__, self._name)

    async def acquire(self) -> Literal[True]:
        """Acquire the dummy semaphore, which is a no-op."""
        return True
    
    async def c_acquire(self) -> Literal[True]:
        return True

    cpdef void release(self):
        """No-op release method."""
    
    cdef void c_release(self):
        """No-op release method."""

    async def __aenter__(self):
        """No-op context manager entry."""
        return self

    async def __aexit__(self, *args):
        """No-op context manager exit."""


cdef class ThreadsafeSemaphore(Semaphore):
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

    def __init__(self, value: Optional[int], name: Optional[str] = None) -> None:
        """
        Initialize the threadsafe semaphore with a given value and optional name.

        Args:
            value: The initial value for the semaphore, should be an integer.
            name (optional): An optional name for the semaphore.
        """
        assert isinstance(value, int), f"{value} should be an integer."
        super().__init__(value, name=name)
        
        self.use_dummy = value is -1
        if self.use_dummy:
            self.semaphores = {}
            self.dummy = DummySemaphore(name=name)
        else:
            self.semaphores: DefaultDict[Thread, Semaphore] = defaultdict(lambda: Semaphore(value, name=self._name))  # type: ignore [arg-type]
            self.dummy = None

    def __len__(self) -> int:
        return sum(len(sem._waiters) for sem in self.semaphores.values())

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
    
    cdef Semaphore c_get_semaphore(self):
        return self.dummy if self.use_dummy else self.semaphores[current_thread()]

    async def __aenter__(self):
        await self.c_get_semaphore().c_acquire()

    async def __aexit__(self, *args):
        self.c_get_semaphore().c_release()
