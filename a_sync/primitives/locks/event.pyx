# cython: boundscheck=False
"""
This module provides an enhanced version of asyncio.Event with additional debug logging to help detect deadlocks.
"""

import sys
from asyncio import AbstractEventLoop, Future, get_event_loop, sleep
from libc.stdint cimport uint16_t
from libc.stdlib cimport malloc, free
from libc.string cimport strcpy
from libc.time cimport time
from weakref import ref

from a_sync._typing import *
from a_sync.primitives._debug cimport _DebugDaemonMixin, _LoopBoundMixin

cdef extern from "time.h":
    ctypedef long time_t


async def _return_true():
    return True


cdef bint _loop_kwarg_deprecated = sys.version_info >= (3, 10)

cdef class CythonEvent(_DebugDaemonMixin):
    """
    An asyncio.Event with additional debug logging to help detect deadlocks.

    This event class extends asyncio.Event by adding debug logging capabilities. It logs
    detailed information about the event state and waiters, which can be useful for
    diagnosing and debugging potential deadlocks.
    """
    def __cinit__(self):
        self._waiters = []
        
    def __init__(
        self,
        name: str = "",
        debug_daemon_interval: int = 300,
        *,
        loop: Optional[AbstractEventLoop] = None,
    ):
        """
        Initializes the Event.

        Args:
            name (str): An optional name for the event, used in debug logs.
            debug_daemon_interval (int): The interval in seconds for the debug daemon to log information.
            loop (Optional[AbstractEventLoop]): The event loop to use.
        """
        if _loop_kwarg_deprecated:
            _LoopBoundMixin.__init__(self)
        else:
            _LoopBoundMixin.__init__(self, loop=loop)

        # backwards compatability
        if hasattr(self, "_loop"):
            self._loop = self._loop or get_event_loop()
        if debug_daemon_interval > 65535:
            raise ValueError(f"'debug_daemon_interval' is stored as a uint16 and must be less than 65535")
        self._debug_daemon_interval = debug_daemon_interval
        # we need a constant to coerce to char*
        cdef bytes encoded_name = name.encode("utf-8")
        cdef Py_ssize_t length = len(encoded_name)

        # Allocate memory for the char* and add 1 for the null character
        self.__name = <char*>malloc(length + 1)
        """An optional name for the counter, used in debug logs."""

        if self.__name == NULL:
            raise MemoryError("Failed to allocate memory for __name.")
        # Copy the bytes data into the char*
        strcpy(self.__name, encoded_name)

    def __dealloc__(self):
        # Free the memory allocated for __name
        if self.__name is not NULL:
            free(self.__name)

    def __repr__(self) -> str:
        cdef str label = (
            "name={}".format(self.__name.decode("utf-8"))
            if self.__name
            else "object"
        )
        
        cdef str status = "set" if self._value else "unset"
        
        if len_waiters := len(self._waiters):
            status += ", waiters:{}".format(len_waiters)
                
        return "<{}.{} {} at {} [{}]>".format(
            self.__class__.__module__, 
            self.__class__.__name__, 
            label,
            hex(id(self)),
            status,
        )

    cpdef bint is_set(self):
        """Return True if and only if the internal flag is true."""
        return self._value

    cpdef void set(self):
        """Set the internal flag to true. All coroutines waiting for it to
        become true are awakened. Coroutine that call wait() once the flag is
        true will not block at all.
        """
        cdef object fut

        if not self._value:
            self._value = True

            for fut in self._waiters:
                if _is_not_done(fut):
                    fut.set_result(True)

    cpdef void clear(self):
        """Reset the internal flag to false. Subsequently, coroutines calling
        wait() will block until set() is called to set the internal flag
        to true again."""
        self._value = False

    cpdef object wait(self):
        """Block until the internal flag is true.

        If the internal flag is true on entry, return True
        immediately.  Otherwise, block until another coroutine calls
        set() to set the flag to true, then return True.

        Returns:
            True when the event is set.
        """
        return self.c_wait()
    
    cdef object c_wait(self):
        if self._value:
            return _return_true()

        self._c_ensure_debug_daemon((),{})

        cdef object fut = Future(loop=self._c_get_loop())
        self._waiters.append(fut)
        return self.__wait(fut)

    @property
    def _name(self) -> str:
        return self.__name.decode("utf-8")
    
    async def __wait(self, fut: Future) -> Literal[True]:
        try:
            await fut
            return True
        finally:
            self._waiters.remove(fut)

    async def _debug_daemon(self) -> None:
        """
        Periodically logs debug information about the event state and waiters.

        This code will only run if `self.logger.isEnabledFor(logging.DEBUG)` is True. You do not need to include any level checks in your custom implementations.
        """
        cdef time_t start, now 
        cdef object weakself = ref(self)
        cdef unsigned int loops = 0
        cdef uint16_t interval = self._debug_daemon_interval

        start = time(NULL)
        while (self := weakself()) and not self._value:
            if loops:
                now = time(NULL)
                self.get_logger().debug(
                    "Waiting for %s for %sm", self, round((now - start) / 60, 2)
                )
            del self  # no need to hold a reference here
            await sleep(interval)
            loops += 1                


cdef inline bint _is_not_done(fut: Future):
    return <str>fut._state == "PENDING"
