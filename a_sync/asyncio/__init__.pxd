cdef object ccreate_task_simple(object coro)
cdef object ccreate_task(object coro, str name, bint skip_gc_until_done, bint log_destroy_pending)