from typing import Callable, Optional


cdef object _NOT_FOUND = object()

cdef class cached_property_unsafe:
    """A non-threadsafe implementation of functools.cached_property, intended for use in asyncio applications"""

    def __cinit__(self):
        self._attrname = None

    def __init__(self, func):
        self._func = func
        self._doc = func.__doc__
    
    @property
    def __doc__(self) -> Optional[str]:
        return self._doc
    
    @property
    def attrname(self) -> Optional[str]:
        return self._attrname
    
    @property
    def func(self) -> Callable:
        return self._func

    def __set_name__(self, owner, name):
        if self._attrname is None:
            self._attrname = name
        elif name != self._attrname:
            raise TypeError(
                "Cannot assign the same cached_property to two different names "
                f"({self._attrname!r} and {name!r})."
            )

    def __get__(self, instance, owner):
        if instance is None:
            return self
        if self._attrname is None:
            raise TypeError(
                "Cannot use cached_property instance without calling __set_name__ on it.")
        try:
            cache = instance.__dict__
        except AttributeError:  # not all objects have __dict__ (e.g. class defines slots)
            msg = (
                f"No '__dict__' attribute on {type(instance).__name__!r} "
                f"instance to cache {self._attrname!r} property."
            )
            raise TypeError(msg) from None
        val = cache.get(self._attrname, _NOT_FOUND)
        if val is _NOT_FOUND:
            val = self._func(instance)
            try:
                cache[self._attrname] = val
            except TypeError:
                msg = (
                    f"The '__dict__' attribute on {type(instance).__name__!r} instance "
                    f"does not support item assignment for caching {self._attrname!r} property."
                )
                raise TypeError(msg) from None
        return val
