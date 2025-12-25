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

from cpython.unicode cimport PyUnicode_CompareWithASCIIString

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

    This enhanced event class adds debug logging to the typical asyncio.Event behavior,
    enabling detailed diagnosis on potential deadlocks.

    See Also:
        :class:`~a_sync.primitives._debug._LoopBoundMixin`
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
        Initializes the event.

        Args:
            name (str): An optional name for the event, used in debug logs.
            debug_daemon_interval (int): The interval in seconds at which the debug daemon logs event information.
            loop (Optional[AbstractEventLoop]): An optional event loop to associate with the event.

        Examples:
            Creating an event with a custom name and default interval:
            
                >>> from asyncio import get_event_loop
                >>> evt = CythonEvent(name="my_event", debug_daemon_interval=300, loop=get_event_loop())
                >>> print(evt._name)
                my_event

            Creating an event with an empty name:
            
                >>> evt2 = CythonEvent()
                >>> print(evt2._name)
                ''

        See Also:
            :meth:`~a_sync.primitives._debug._LoopBoundMixin._get_loop`
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
        """An optional name for the event, used in debug logs."""

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
        become true are awakened. Coroutines that call wait() once the flag is
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
        wait() will block until set() is called to set the flag to true again.
        """
        self._value = False

    cpdef object wait(self):
        """Block until the internal flag is true.

        If the internal flag is true on entry, return True immediately.
        Otherwise, block until another coroutine calls set() to set the flag
        to true, then return True.

        Returns:
            True when the event is set.
            
        Examples:
            >>> evt = CythonEvent(name="demo")
            >>> res = await evt.wait()
            >>> assert res is True

        See Also:
            :meth:`c_wait`
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

        This method is activated when debug logging is enabled for the event's logger.
        It periodically computes and logs the duration the event has been waiting and the count of waiting coroutines.
        
        Examples:
            >>> # Assume debug logs are enabled for the event's logger.
            >>> await event._debug_daemon()

        See Also:
            :func:`~asyncio.sleep`
            :attr:`~a_sync.primitives.locks.event.DEBUG`
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
    return PyUnicode_CompareWithASCIIString(fut._state, b"PENDING") == 0