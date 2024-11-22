
from a_sync.primitives._debug cimport _DebugDaemonMixin
from a_sync.primitives.locks.event cimport CythonEvent as Event

cdef class CounterLock(_DebugDaemonMixin):
    cdef char* __name
    cdef int _value
    cdef dict[int, Event] _events
    cpdef bint is_ready(self, int v)
    cdef bint c_is_ready(self, int v)
    cpdef void set(self, int value)
    cdef void c_set(self, int value)