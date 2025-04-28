# cython: profile=False
# cython: linetrace=False
import asyncio


cdef class sleep0:
    """Skip one event loop run cycle.

    This is a hacky helper for 'asyncio.sleep()', used
    when the 'delay' is set to 0. It yields exactly one
    time (which Task.__step knows how to handle) instead
    of creating a Future object. We monkey patch asyncio
    with our helper so it "just works" without you doing
    anything.
    
    While asyncio.sleep(0) is already very well-optimized,
    this equivalent helper consumes about 10% less compute
    than asyncio's equivalent internal helper.
    """

    cdef bint done
    cdef object result

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


asyncio.tasks.__sleep0 = sleep0
