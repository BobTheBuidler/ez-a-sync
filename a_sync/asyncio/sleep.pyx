# cython: profile=False
# cython: linetrace=False

cdef class sleep0:
    """
    While asyncio.sleep(0) is already very well-optimized,
    this equivalent helper consumes about 10% less compute.
    """

    cdef bint done

    def __cinit__(self) -> None:
        self.done = False
    
    def __await__(self) -> sleep0:
        return self
    
    def __iter__(self) -> sleep0:
        return self
    
    def __next__(self) -> None:
        if self.done:
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
