cdef class _ASyncBoundMethod:
    cdef readonly object __weakself__
    cdef readonly bint _is_async_def
cdef bint _is_a_sync_instance(object instance)
cdef void _update_cache_timer(str field_name, object instance, _ASyncBoundMethod bound)
