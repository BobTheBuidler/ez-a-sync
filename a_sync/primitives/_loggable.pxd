cdef class _LoggerMixin:
    cdef object _logger
    cdef object get_logger(self)
    cdef bint check_debug_logs_enabled(self)