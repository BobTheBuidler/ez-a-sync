cdef class ModifierManager:
    cdef readonly dict[str, object] _modifiers
    cpdef object apply_async_modifiers(self, coro_fn)