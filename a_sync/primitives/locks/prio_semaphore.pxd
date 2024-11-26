from a_sync.primitives.locks.semaphore cimport Semaphore

cdef class _AbstractPrioritySemaphore(Semaphore):
    cdef dict[object, _AbstractPrioritySemaphoreContextManager] _context_managers
    cdef Py_ssize_t _capacity
    cdef list _potential_lost_waiters
    cdef object _top_priority
    cdef object _context_manager_class
    cdef object c_getitem(self, object priority)
    cdef dict[object, int] _count_waiters(self)

cdef class _AbstractPrioritySemaphoreContextManager(Semaphore):
    cdef _AbstractPrioritySemaphore _parent
    cdef object _priority
    cdef str _priority_name
    cpdef str _repr_no_parent_(self)
    cdef str _c_repr_no_parent_(self)

cdef class _PrioritySemaphoreContextManager(_AbstractPrioritySemaphoreContextManager):
    pass

cdef class PrioritySemaphore(_AbstractPrioritySemaphore):
    pass
