from a_sync.a_sync.modifiers.manager cimport ModifierManager

cdef public object ASyncFunction
cdef public object ASyncFunctionAsyncDefault
cdef public object ASyncFunctionSyncDefault

cdef class _ModifiedMixin:
    cdef readonly ModifierManager modifiers
    cdef public object __wrapped__
    cdef object _asyncify(self, object func)

    cdef str __default
    cdef object __await
    cdef str get_default(self)
    cdef object get_await(self)

cdef void _validate_wrapped_fn(object fn)