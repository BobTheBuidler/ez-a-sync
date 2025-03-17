cdef class cached_property_unsafe:
    cdef readonly object func
    cdef readonly str attrname
    cdef str _doc

cdef object wraps(wrapped)
cpdef object update_wrapper(wrapper, wrapped)