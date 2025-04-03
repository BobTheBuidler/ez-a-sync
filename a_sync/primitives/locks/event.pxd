from libc.stdint cimport uint16_t

from a_sync.primitives._debug cimport _DebugDaemonMixin

cdef class CythonEvent(_DebugDaemonMixin):
    """
    An asyncio.Event with additional debug logging to help detect deadlocks.

    This event class extends asyncio.Event by adding debug logging capabilities. It logs
    detailed information about the event state and waiters, which can be useful for
    diagnosing and debugging potential deadlocks.
    """

    cdef bint _value
    cdef list _waiters
    cdef char* __name
    cdef uint16_t _debug_daemon_interval
    cpdef bint is_set(self)
    cpdef void set(self)
    cpdef void clear(self)
    cpdef object wait(self)
    cdef object c_wait(self)