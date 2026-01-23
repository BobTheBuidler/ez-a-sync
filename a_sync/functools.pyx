from typing import Optional


cdef object _NOT_FOUND = object()

cdef class cached_property_unsafe:
    """A non-threadsafe implementation of functools.cached_property, intended for use in asyncio applications"""

    def __cinit__(self, object func):
        self.func = func
        self.attrname = None
        self._doc = func.__doc__
    
    @property
    def __doc__(self) -> Optional[str]:
        return self._doc

    def __set_name__(self, owner, str name):
        cdef str existing_name = self.attrname
        if existing_name is None:
            self.attrname = name
        elif name != existing_name:
            raise TypeError(
                "Cannot assign the same cached_property to two different names "
                f"({existing_name!r} and {name!r})."
            )

    def __get__(self, instance, owner):
        cdef str attrname
        cdef dict cache
        if instance is None:
            return self
        attrname = self.attrname
        if attrname is None:
            raise TypeError(
                "Cannot use cached_property instance without calling __set_name__ on it.")
        try:
            cache = instance.__dict__
        except AttributeError:  # not all objects have __dict__ (e.g. class defines slots)
            msg = (
                f"No '__dict__' attribute on {type(instance).__name__!r} "
                f"instance to cache {attrname!r} property."
            )
            raise TypeError(msg) from None
        val = cache.get(attrname, _NOT_FOUND)
        if val is _NOT_FOUND:
            val = self.func(instance)
            try:
                cache[attrname] = val
            except TypeError:
                msg = (
                    f"The '__dict__' attribute on {type(instance).__name__!r} instance "
                    f"does not support item assignment for caching {attrname!r} property."
                )
                raise TypeError(msg) from None
        return val


################################################################################
### update_wrapper() and wraps() decorator
################################################################################

# update_wrapper() and wraps() are tools to help write
# wrapper functions that can handle naive introspection

cpdef update_wrapper(wrapper, wrapped):
    """Update a wrapper function to look like the wrapped function

    wrapper is the function to be updated
    wrapped is the original function
    assigned is a tuple naming the attributes assigned directly
    from the wrapped function to the wrapper function (defaults to
    functools.WRAPPER_ASSIGNMENTS)
    updated is a tuple naming the attributes of the wrapper that
    are updated with the corresponding attribute from the wrapped
    function (defaults to functools.WRAPPER_UPDATES)

    `assigned` and `updated` args from the functools implementation have
    been disabled for faster tight loops. Use the implementation in the
    `functools` builtin module if you need to use their functionality.
    """
    try:
        value = getattr(wrapped, '__module__')
    except AttributeError:
        pass
    else:
        setattr(wrapper, '__module__', value)

    try:
        value = getattr(wrapped, '__name__')
    except AttributeError:
        pass
    else:
        setattr(wrapper, '__name__', value)

    try:
        value = getattr(wrapped, '__qualname__')
    except AttributeError:
        pass
    else:
        setattr(wrapper, '__qualname__', value)

    try:
        value = getattr(wrapped, '__doc__')
    except AttributeError:
        pass
    else:
        setattr(wrapper, '__doc__', value)

    try:
        value = getattr(wrapped, '__annotations__')
    except AttributeError:
        pass
    else:
        setattr(wrapper, '__annotations__', value)

    getattr(wrapper, '__dict__').update(getattr(wrapped, '__dict__', {}))
    # Issue #17482: set __wrapped__ last so we don't inadvertently copy it
    # from the wrapped function when updating __dict__
    wrapper.__wrapped__ = wrapped
    # Return the wrapper so this can be used as a decorator via partial()
    return wrapper


cdef wraps(wrapped):
    """Decorator factory to apply update_wrapper() to a wrapper function

    Returns a decorator that invokes update_wrapper() with the decorated
    function as the wrapper argument and the arguments to wraps() as the
    remaining arguments. Default arguments are as for update_wrapper().
    This is a convenience function to simplify applying partial() to
    update_wrapper().

    `assigned` and `updated` args from the functools implementation have
    been disabled for faster tight loops. Use the implementation in the
    `functools` builtin module if you need to use their functionality.

    """
    return lambda wrapper: update_wrapper(wrapper, wrapped)
