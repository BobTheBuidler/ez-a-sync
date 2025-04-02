from a_sync.primitives._debug cimport _DebugDaemonMixin

cdef class Semaphore(_DebugDaemonMixin):
    cdef unsigned long long __value
    cdef object __waiters
    cdef char* _name
    cdef str decode_name(self)
    cdef set _decorated
    cdef dict __dict__
    cpdef bint locked(self)
    cpdef object acquire(self)
    cpdef void release(self)
    cpdef void _wake_up_next(self)
            
cdef class DummySemaphore(Semaphore):
    pass

cdef class ThreadsafeSemaphore(Semaphore):
    cdef object semaphores, dummy
    cdef bint use_dummy
    cdef Semaphore c_get_semaphore(self)
