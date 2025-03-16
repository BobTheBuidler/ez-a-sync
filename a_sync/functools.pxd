cdef class cached_property_unsafe:
    cdef object _func
    cdef str _attrname
    cdef str _doc

cdef object wraps(wrapped)
cpdef object update_wrapper(wrapper, wrapped)