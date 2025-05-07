from a_sync.primitives.locks.semaphore cimport Semaphore

cdef class _AbstractPrioritySemaphore(Semaphore):
    cdef readonly dict[object, _AbstractPrioritySemaphoreContextManager] _context_managers
    cdef readonly Py_ssize_t _capacity
    cdef readonly set _potential_lost_waiters
    cdef readonly object _top_priority
    cdef readonly _AbstractPrioritySemaphoreContextManager _top_priority_manager
    cdef readonly object _context_manager_class
    cpdef object acquire(self)
    cdef _AbstractPrioritySemaphoreContextManager c_getitem(self, object priority)
    cdef dict[object, int] _count_waiters(self)
    cpdef void _wake_up_next(self)

cdef class PrioritySemaphore(_AbstractPrioritySemaphore):
    pass

cdef class _AbstractPrioritySemaphoreContextManager(Semaphore):
    cdef readonly _AbstractPrioritySemaphore _parent
    cdef readonly object _priority
    cdef readonly str _priority_name
    cpdef str _repr_no_parent_(self)

cdef class _PrioritySemaphoreContextManager(_AbstractPrioritySemaphoreContextManager):
    pass
