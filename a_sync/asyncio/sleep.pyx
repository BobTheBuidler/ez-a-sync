# cython: profile=False
# cython: linetrace=False

cdef class sleep0:
    cdef bint done
    
    def __await__(self) -> sleep0:
        return self
    
    def __iter__(self) -> sleep0:
        return self
    
    def __next__(self) -> None:
        if self.done:
            raise StopIteration
        self.done = True
