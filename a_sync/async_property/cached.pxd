ctypedef str FieldName
ctypedef object CacheValue

cdef public str ASYNC_PROPERTY_ATTR = "__async_property__"

cdef class AsyncCachedPropertyInstanceState:
    cdef readonly dict[FieldName, CacheValue] cache
    cdef readonly object locks
    cdef object get_lock(self, str field_name)
    cdef object get_cache_value(self, str field_name)