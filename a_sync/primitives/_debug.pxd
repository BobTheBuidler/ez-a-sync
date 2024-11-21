from a_sync.primitives._loggable cimport _LoggerMixin

cdef class _LoopBoundMixin(_LoggerMixin):
    cdef object __loop
    cpdef object _get_loop(self)
    cdef object _c_get_loop(self)

cdef class _DebugDaemonMixin(_LoopBoundMixin):
    cdef object _daemon
