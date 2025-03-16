from _typeshed import Incomplete
from typing import Any, Callable, Generic, TypeVar

I = TypeVar("I")
T = TypeVar("T")

class cached_property_unsafe(Generic[I, T]):
    """A non-threadsafe implementation of functools.cached_property, intended for use in asyncio applications"""

    func: Callable[[I], T]
    attrname: Incomplete
    __doc__: Incomplete
    def __init__(self, func: Callable[[I], T]) -> None: ...
    def __set_name__(self, owner, name: str) -> None: ...
    def __get__(self, instance: I, owner: Incomplete | None = None) -> T: ...
    __class_getitem__: Incomplete

def update_wrapper(wrapper, wrapped):
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
        value = getattr(wrapped, "__module__")
    except AttributeError:
        pass
    else:
        setattr(wrapper, "__module__", value)

    try:
        value = getattr(wrapped, "__name__")
    except AttributeError:
        pass
    else:
        setattr(wrapper, "__name__", value)

    try:
        value = getattr(wrapped, "__qualname__")
    except AttributeError:
        pass
    else:
        setattr(wrapper, "__qualname__", value)

    try:
        value = getattr(wrapped, "__doc__")
    except AttributeError:
        pass
    else:
        setattr(wrapper, "__doc__", value)

    try:
        value = getattr(wrapped, "__annotations__")
    except AttributeError:
        pass
    else:
        setattr(wrapper, "__annotations__", value)

    getattr(wrapper, "__dict__").update(getattr(wrapped, "__dict__", {}))
    # Issue #17482: set __wrapped__ last so we don't inadvertently copy it
    # from the wrapped function when updating __dict__
    wrapper.__wrapped__ = wrapped
    # Return the wrapper so this can be used as a decorator via partial()
    return wrapper
