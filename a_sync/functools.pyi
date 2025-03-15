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
