cdef class _ModifiedMixin:
    cdef public object modifiers
    cdef public object wrapped
    cpdef object _asyncify(self, object func)
    
    cdef str __default
    cdef object __await
    cdef str get_default(self)
    cdef object get_await(self)
