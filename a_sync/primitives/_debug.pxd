from a_sync.primitives._loggable cimport _LoggerMixin

cdef class _LoopBoundMixin(_LoggerMixin):
    cdef object __loop
    cpdef object _get_loop(self)
    cdef object _c_get_loop(self)

cdef class _DebugDaemonMixin(_LoopBoundMixin):
    cdef object _daemon
    cdef bint _has_daemon
    cdef void _c_ensure_debug_daemon(self, tuple[object] args, dict[str, object] kwargs)
    cdef object _c_start_debug_daemon(self, tuple[object] args, dict[str, object] kwargs)
