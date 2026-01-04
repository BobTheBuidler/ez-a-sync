from typing import Any, Callable, Generic, TypeVar

I = TypeVar("I")
T = TypeVar("T")

class cached_property_unsafe(Generic[I, T]):
    """A non-threadsafe implementation of functools.cached_property, intended for use in asyncio applications"""

    func: Callable[[I], T]
    attrname: str
    __doc__: str | None
    def __init__(self, func: Callable[[I], T]) -> None: ...
    def __set_name__(self, owner: type[I], name: str) -> None: ...
    def __get__(self, instance: I, owner: type[I] | None = None) -> T: ...
    def __class_getitem__(cls, item: object) -> type[cached_property_unsafe[Any, Any]]: ...

def update_wrapper(wrapper: Callable, wrapped: Callable) -> None:
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
