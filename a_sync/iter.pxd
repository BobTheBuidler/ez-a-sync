cdef class _ASyncGeneratorFunction:
    cdef readonly object _cache_handle
    cdef readonly object __weakself__
    cdef inline void _set_cache_handle(self, object handle)
    cdef inline object _get_cache_handle(self, object instance)
    cdef void __cancel_cache_handle(self)
