
from a_sync.primitives._debug cimport _DebugDaemonMixin
from a_sync.primitives.locks.event cimport CythonEvent as Event

cdef class CounterLock(_DebugDaemonMixin):
    cdef char* __name
    cdef long long _value
    cdef dict[long long, Event] _events
    cpdef bint is_ready(self, long long v)
    cdef bint c_is_ready(self, long long v)
    cpdef void set(self, long long value)
    cdef void c_set(self, long long value)