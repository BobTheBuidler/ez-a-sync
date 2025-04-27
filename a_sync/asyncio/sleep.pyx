# cython: profile=False
# cython: linetrace=False

cdef sleep0[:] ready = []

cdef class sleep0:
    cdef bint done
    
    def __await__(self) -> sleep0:
        return self
    
    def __iter__(self) -> sleep0:
        return self
    
    def __next__(self) -> None:
        if self.done:
            self.done = False
            ready.append(self)
            raise StopIteration
        self.done = True

    # For Python 3.7+ compatibility (PEP 479)
    def send(self, value) -> None:
        if self.done:
            raise StopIteration
        self.done = True

    def throw(self, typ, val=None, tb=None):
        # Propagate StopIteration or exceptions
        raise typ if val is None else typ(val)
