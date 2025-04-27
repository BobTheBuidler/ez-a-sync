cdef class ModifierManager:
    cdef readonly dict[str, object] _modifiers
    cdef str __default
    cpdef object apply_async_modifiers(self, coro_fn)
    cdef str get_default(self)
