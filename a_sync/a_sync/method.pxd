from a_sync.a_sync.function cimport _ASyncFunction
cdef class _ASyncBoundMethod(_ASyncFunction):
    cdef readonly object __weakself__
    cdef readonly bint _is_async_def
    cdef readonly object _cache_handle
    cdef object c_map(self, tuple iterables, object concurrency, str task_name, dict kwargs)
    cdef object __c_self__(self)
cdef bint _is_a_sync_instance(object instance)
cdef void _update_cache_timer(str field_name, object instance, _ASyncBoundMethod bound)
