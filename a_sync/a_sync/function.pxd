from a_sync.a_sync.modifiers.manager cimport ModifierManager

cdef class _ModifiedMixin:
    cdef readonly ModifierManager modifiers
    cdef public object __wrapped__
    cdef object _asyncify(self, object func)

    cdef str __default
    cdef object __await
    cdef str get_default(self)
    cdef object get_await(self)

cdef class _ASyncFunction(_ModifiedMixin):
    cdef readonly object _fn
    cdef bint __sync_default
    cdef bint __sync_default_cached
    cdef bint __async_def
    cdef bint __async_def_cached
    cdef object __asyncified
    cdef object __modified_fn
    cdef object __async_wrap
    cdef object __sync_wrap

cdef void _validate_wrapped_fn(object fn)