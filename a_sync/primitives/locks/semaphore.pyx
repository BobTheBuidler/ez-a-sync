"""
This module provides various semaphore implementations, including a debug-enabled semaphore,
a dummy semaphore that does nothing, and a threadsafe semaphore for use in multi-threaded applications.
"""

import asyncio
import collections
import threading
from libc.string cimport strcpy
from libc.stdlib cimport malloc, free
from typing import Container, Literal, List, Optional, Set

from a_sync._typing import CoroFn, P, T
from a_sync.functools cimport wraps
from a_sync.primitives._debug cimport _DebugDaemonMixin, _LoopBoundMixin


# cdef asyncio
cdef object iscoroutinefunction = asyncio.iscoroutinefunction
cdef object sleep = asyncio.sleep
cdef object CancelledError = asyncio.CancelledError
cdef object Future = asyncio.Future
del asyncio

# cdef collections
cdef object defaultdict = collections.defaultdict
cdef object deque = collections.deque
del collections

# cdef threading
cdef object current_thread = threading.current_thread
cdef object Thread = threading.Thread
del threading


async def _noop() -> Literal[True]:
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
        self._Semaphore__waiters = deque()
        self._decorated: Set[str] = set()
    
    def __init__(
        self, 
        value: int = 1, 
        str name = "", 
        object loop = None,
    ) -> None:
        """
        Initialize the semaphore with a given value and optional name for debugging.

        Args:
            value: The initial value for the semaphore.
            name (optional): An optional name used only to provide useful context in debug logs.
        """
        _LoopBoundMixin.__init__(self, loop=loop)
        if value < 0:
            raise ValueError("Semaphore initial value must be >= 0")

        try:
            self._Semaphore__value = value
        except OverflowError as e:
            if value < 0:
                raise ValueError("'value' must be a positive integer") from e.__cause__
            raise OverflowError(
                {"error": str(e), "value": value, "max value": 18446744073709551615},
                "If you need a Semaphore with a larger value, you should just use asyncio.Semaphore",
            ) from e.__cause__
            
        # we need a constant to coerce to char*
        cdef bytes encoded_name = (name or getattr(self, "__origin__", "")).encode("utf-8")
        cdef Py_ssize_t length = len(encoded_name)

        # Allocate memory for the char* and add 1 for the null character
        self._name = <char*>malloc(length + 1)
        """An optional name for the counter, used in debug logs."""

        if self._name == NULL:
            raise MemoryError("Failed to allocate memory for __name.")
        # Copy the bytes data into the char*
        strcpy(self._name, encoded_name)

    def __dealloc__(self):
        # Free the memory allocated for _name
        if self._name is not NULL:
            free(self._name)

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
        representation = f"<{self.__class__.__name__} name={self.decode_name()} value={self._Semaphore__value} waiters={len(self)}>"
        if self._decorated:
            detail = next(iter(decorated)) if len(decorated := self._decorated) == 1 else decorated
            representation = f"{representation[:-1]} decorates={detail}"
        return representation

    async def __aenter__(self):
        await self.acquire()
        # We have no use for the "as ..."  clause in the with
        # statement for locks.
        return None

    async def __aexit__(self, exc_type, exc, tb):
        self.release()

    cpdef bint locked(self):
        """Returns True if semaphore cannot be acquired immediately."""
        if self._Semaphore__value == 0:
            return True
        for w in self._Semaphore__waiters:
            if _is_not_cancelled(w):
                return True

    def __len__(self) -> int:
        return len(self._Semaphore__waiters)

    def decorate(self, fn: CoroFn[P, T]) -> CoroFn[P, T]:
        """
        Wrap a coroutine function to ensure it runs with the semaphore.

        Example:
            semaphore = Semaphore(5)

            @semaphore
            async def limited():
                return 1
        """
        if not iscoroutinefunction(fn):
            raise TypeError(f"{fn} must be a coroutine function")

        @wraps(fn)
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
        if self._Semaphore__value <= 0:
            self._c_ensure_debug_daemon((),{})

        if not self.locked():
            self._Semaphore__value -= 1
            return _noop()

        return self.__acquire()

    async def __acquire(self) -> Literal[True]:
        # Finally block should be called before the CancelledError
        # handling as we don't want CancelledError to call
        # _wake_up_first() and attempt to wake up itself.
        
        cdef object fut = self._c_get_loop().create_future()
        self._Semaphore__waiters.append(fut)
        try:
            try:
                await fut
            finally:
                self._Semaphore__waiters.remove(fut)
        except CancelledError:
            if _is_not_cancelled(fut):
                self._Semaphore__value += 1
                self._wake_up_next()
            raise

        if self._Semaphore__value > 0:
            self._wake_up_next()

        return True

    cpdef void release(self):
        """Release a semaphore, incrementing the internal counter by one.

        When it was zero on entry and another coroutine is waiting for it to
        become larger than zero again, wake up that coroutine.
        """
        self._Semaphore__value += 1
        self._wake_up_next()

    @property
    def name(self) -> str:
        return self.decode_name()
    
    cdef str decode_name(self):
        return (self._name or b"").decode("utf-8")

    @property
    def _value(self) -> int:
        # required for subclass compatability
        return self._Semaphore__value
    
    @_value.setter
    def _value(self, unsigned long long value):
        # required for subclass compatability
        self._Semaphore__value = value

    @property
    def _waiters(self) -> List[Future]:
        # required for subclass compatability
        return self._Semaphore__waiters
    
    @_waiters.setter
    def _waiters(self, value: Container):
        # required for subclass compatability
        self._Semaphore__waiters = value

    cpdef void _wake_up_next(self):
        """Wake up the first waiter that isn't done."""
        if not self._Semaphore__waiters:
            return

        for fut in self._Semaphore__waiters:
            if _is_not_done(fut):
                self._Semaphore__value -= 1
                fut.set_result(True)
                return
            
    async def _debug_daemon(self) -> None:
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
        cdef object waiters = self._Semaphore__waiters
        cdef set decorated = self._decorated
        cdef object log = self.get_logger().debug
        while waiters:
            await sleep(60)
            if waiters:
                len_decorated = len(decorated)
                if len_decorated == 0:
                    log("%s has %s waiters", self, len(self))
                elif len_decorated == 1:
                    log(
                        "%s has %s waiters for %s",
                        self,
                        len(self),
                        next(iter(decorated)),
                    )
                else:
                    log(
                        "%s has %s waiters for any of: %s",
                        self,
                        len(self),
                        decorated,
                    )


cdef inline bint _is_not_done(fut: Future):
    return <str>fut._state == "PENDING"

cdef inline bint _is_not_cancelled(fut: Future):
    return <str>fut._state != "CANCELLED"


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
        self._Semaphore__value = 0
        self._Semaphore__waiters = deque()
        self._decorated = None

    def __init__(self, name: Optional[str] = None):
        """
        Initialize the dummy semaphore with an optional name.

        Args:
            name (optional): An optional name for the dummy semaphore.
        """
            
        # we need a constant to coerce to char*
        cdef bytes encoded_name = (name or getattr(self, "__origin__", "")).encode("utf-8")
        cdef Py_ssize_t length = len(encoded_name)

        # Allocate memory for the char* and add 1 for the null character
        self._name = <char*>malloc(length + 1)
        """An optional name for the counter, used in debug logs."""

        if self._name == NULL:
            raise MemoryError("Failed to allocate memory for _name.")
            
        # Copy the bytes data into the char*
        strcpy(self._name, encoded_name)

    def __repr__(self) -> str:
        return "<{} name={}>".format(self.__class__.__name__, self.decode_name())

    async def acquire(self) -> Literal[True]:
        """Acquire the dummy semaphore, which is a no-op."""
        return True

    cpdef void release(self):
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
        Semaphore.__init__(self, value, name=name)
        
        self.use_dummy = value is -1
        if self.use_dummy:
            self.semaphores = {}
            self.dummy = DummySemaphore(name=name)
        else:
            self.semaphores: DefaultDict[Thread, Semaphore] = defaultdict(lambda: Semaphore(value, name=name))  # type: ignore [arg-type]
            self.dummy = None

    def __len__(self) -> int:
        cdef dict[object, Semaphore] semaphores = self.semaphores
        return sum(map(len, semaphores.values()))

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
        await self.c_get_semaphore().acquire()

    async def __aexit__(self, *args):
        self.c_get_semaphore().release()
