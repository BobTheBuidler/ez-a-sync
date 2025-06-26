"""
This module provides various semaphore implementations, including a debug‐enabled semaphore,
a dummy semaphore that does nothing, and a threadsafe semaphore for use in multi‐threaded applications.
"""

import asyncio
import collections
import threading
from libc.string cimport strcpy
from libc.stdlib cimport malloc, free
from typing import Container, Literal, List, Optional, Set

from cpython.unicode cimport PyUnicode_CompareWithASCIIString

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

        ::

            semaphore = Semaphore(5)

            async def limited():
                async with semaphore:
                    return 1

        like this:

        ::

            semaphore = Semaphore(5)

            @semaphore
            async def limited():
                return 1

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
        Initialize the semaphore with a given value, an optional name for debugging, and an optional loop.

        Args:
            value: The initial value for the semaphore.
            name (optional): An optional string used only to provide useful context in debug logs.
            loop (optional): Reserved parameter for binding the semaphore to a specific event loop.
                This parameter is no longer used and should be left as None.

        Raises:
            ValueError: If the initial value is negative.
            MemoryError: If memory allocation for the semaphore name fails.
            OverflowError: If the value is too large.
        
        Examples:
            ::
            
                # Normal initialization of a semaphore with 3 permits.
                semaphore = Semaphore(3, name="mySemaphore")

                # The 'loop' parameter is reserved; simply leave it as None.
                semaphore = Semaphore(3, name="mySemaphore", loop=None)

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
        cdef bytes encoded_name
        try:
            encoded_name = (name or getattr(self, "__origin__", "")).encode("utf-8")
        except AttributeError:
            # just a failsafe, please use string inputs
            encoded_name = repr(name).encode("utf-8")

        # Allocate memory for the char* and add 1 for the null character
        cdef Py_ssize_t length = len(encoded_name)
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
            ::
            
                semaphore = Semaphore(5)

                @semaphore
                async def limited():
                    return 1

        See Also:
            :meth:`decorate`
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
        """Returns True if the semaphore cannot be acquired immediately."""
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
            ::
            
                semaphore = Semaphore(5)

                @semaphore
                async def limited():
                    return 1

        Raises:
            TypeError: If the provided function is not a coroutine function.

        See Also:
            :meth:`__call__`
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

        If the internal counter is greater than zero on entry, it is decremented by one and a no-op awaitable is returned.
        If the counter is zero or less, the debug daemon is started and the coroutine waits until the semaphore is available.
        
        Returns:
            An awaitable that resolves to True when the semaphore is successfully acquired.

        See Also:
            :meth:`release`
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

        When the counter is zero on entry and another coroutine is waiting for it to
        become greater than zero, this method wakes up that coroutine.

        See Also:
            :meth:`acquire`
        """
        self._Semaphore__value += 1
        self._wake_up_next()

    @property
    def name(self) -> str:
        """Return the decoded name of this semaphore."""
        return self.decode_name()
    
    cdef str decode_name(self):
        """Decode the name stored in the C-allocated memory block for debug logs."""
        return (self._name or b"").decode("utf-8")

    @property
    def _value(self) -> int:
        # required for subclass compatibility
        return self._Semaphore__value
    
    @_value.setter
    def _value(self, unsigned long long value):
        # required for subclass compatibility
        self._Semaphore__value = value

    @property
    def _waiters(self) -> List[Future]:
        # required for subclass compatibility
        return self._Semaphore__waiters
    
    @_waiters.setter
    def _waiters(self, value: Container):
        # required for subclass compatibility
        self._Semaphore__waiters = value

    cpdef void _wake_up_next(self):
        """Wake up the first waiter that is still pending.

        This method searches the waiters list and, upon finding a waiter that has not yet completed,
        decrements the semaphore value and sets the waiter's result to True.
        """
        if not self._Semaphore__waiters:
            return

        for fut in self._Semaphore__waiters:
            if _is_not_done(fut):
                self._Semaphore__value -= 1
                fut.set_result(True)
                return
            
    async def _debug_daemon(self) -> None:
        """
        Daemon coroutine (runs in a background task) that emits a debug log every minute while the semaphore has waiters.

        This method is part of the :class:`_DebugDaemonMixin` and is used to provide detailed logging
        about the semaphore's state during contention.

        Examples:
            ::
            
                semaphore = Semaphore(5)
                
                async def monitor():
                    await semaphore._debug_daemon()

        Note:
            This coroutine runs only if :attr:`logger.isEnabledFor(DEBUG)` is True.

        See Also:
            - :meth:`_ensure_debug_daemon`
            - :attr:`logger`
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
    return PyUnicode_CompareWithASCIIString(fut._state, b"PENDING") == 0

cdef inline bint _is_not_cancelled(fut: Future):
    return PyUnicode_CompareWithASCIIString(fut._state, b"CANCELLED") != 0


cdef class DummySemaphore(Semaphore):
    """
    A dummy semaphore that implements the standard :class:`asyncio.Semaphore` API but performs no synchronization.

    This class is useful for scenarios where a semaphore interface is required but no actual blocking or synchronization is needed.
    It immediately returns when acquired and does nothing on release.

    Example:
        ::
        
            dummy_semaphore = DummySemaphore()

            async def no_op():
                async with dummy_semaphore:
                    return 1

    See Also:
        :class:`Semaphore`
    """

    def __cinit__(self):
        self._Semaphore__value = 0
        self._Semaphore__waiters = deque()
        self._decorated = None

    def __init__(self, name: Optional[str] = None):
        """
        Initialize the dummy semaphore with an optional name.

        Args:
            name (optional): An optional string to identify the dummy semaphore in debug logs.
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
        """Acquire the dummy semaphore, which is a no-op.

        Returns:
            Always returns True immediately.

        Examples:
            ::
            
                dummy_semaphore = DummySemaphore()
                result = await dummy_semaphore.acquire()
                # result is True

        """
        return True

    cpdef void release(self):
        """No-op release method.

        Does nothing.
        """

    async def __aenter__(self):
        """No-op context manager entry.

        Returns:
            The dummy semaphore itself.
        """
        return self

    async def __aexit__(self, *args):
        """No-op context manager exit."""
        pass


cdef class ThreadsafeSemaphore(Semaphore):
    """
    A semaphore that works in a multi-threaded environment.

    This semaphore ensures proper behavior even when used across multiple threads and event loops.
    It provides a workaround for edge cases by maintaining a separate semaphore for each thread.
    Specifically:
    
    - If the provided initial value is -1, the semaphore operates in dummy mode by employing a
      :class:`DummySemaphore` (i.e. no actual synchronization is performed).
    - Otherwise, a default dictionary is created mapping each thread to its own :class:`Semaphore`
      instance initialized with the given value.

    Example:
        ::
        
            # Using a normal threadsafe semaphore with 5 permits
            semaphore = ThreadsafeSemaphore(5, name="workerSemaphore")

            async def limited():
                async with semaphore:
                    return 1

            # Using dummy mode (value set to -1) so that acquiring is a no-op.
            dummy_semaphore = ThreadsafeSemaphore(-1, name="dummySemaphore")
            async def non_blocking():
                async with dummy_semaphore:
                    return "immediate"

    See Also:
        :class:`Semaphore` for the base semaphore implementation.
        :class:`DummySemaphore` for the non-blocking version.
    """

    def __init__(self, value: Optional[int], name: Optional[str] = None) -> None:
        """
        Initialize the threadsafe semaphore with a given value and an optional name.

        Args:
            value: The initial semaphore value as an integer. If value is -1,
                this semaphore will use dummy mode and perform no synchronization.
            name (optional): An optional string name for the semaphore, useful for debugging.

        Raises:
            AssertionError: If value is not of type int.
        
        Examples:
            ::
            
                # Normal per-thread semaphore
                semaphore = ThreadsafeSemaphore(5, name="workerSemaphore")
                
                # Dummy semaphore mode (non-blocking behavior)
                dummy = ThreadsafeSemaphore(-1, name="dummySemaphore")
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
        Return the per-thread semaphore associated with the current thread.

        This property dynamically retrieves the appropriate semaphore instance by 
        calling the internal :meth:`c_get_semaphore`. When the ThreadsafeSemaphore
        is configured in dummy mode (i.e. when the initial value is -1), it returns
        the dummy semaphore instance. Otherwise, it returns the thread-specific
        :class:`Semaphore` instance from an internal mapping.

        Examples:
            ::
                # Create a threadsafe semaphore with 5 permits
                semaphore = ThreadsafeSemaphore(5, name="workerSemaphore")
                # Retrieve the semaphore for the current thread
                current_semaphore = semaphore.semaphore
                async with current_semaphore:
                    result = await some_coroutine()

        See Also:
            :meth:`c_get_semaphore` for detailed implementation.
        """
    
    cdef Semaphore c_get_semaphore(self):
        return self.dummy if self.use_dummy else self.semaphores[current_thread()]

    async def __aenter__(self):
        await self.c_get_semaphore().acquire()

    async def __aexit__(self, *args):
        self.c_get_semaphore().release()


cdef inline bint _is_not_done(fut: Future):
    return PyUnicode_CompareWithASCIIString(fut._state, b"PENDING") == 0

cdef inline bint _is_not_cancelled(fut: Future):
    return PyUnicode_CompareWithASCIIString(fut._state, b"CANCELLED") != 0