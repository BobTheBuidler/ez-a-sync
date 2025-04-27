# cython: profile=False
# cython: linetrace=False

cdef class sleep0:
    cdef bint done
    
    cpdef sleep0 __await__(self) noexcept:
        return self
    
    cpdef sleep0 __iter__(self) noexcept:
        return self
    
    cpdef object __next__(self) except NULL:
        if not self.done:
            self.done = True
            return None
        raise StopIteration()
