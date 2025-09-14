from asyncio import Lock
from typing import Any, Callable, Dict, Generic, Optional, TypeVar, Union

from a_sync.async_property.proxy import AwaitableOnly, AwaitableProxy

ProxyType = Union[AwaitableOnly[__T], AwaitableProxy[__T]]

FieldName = str

__I = TypeVar("__I")
__T = TypeVar("__T")

def async_cached_property(
    func: Callable[[__I], __T], *args, **kwargs
) -> "AsyncCachedPropertyDescriptor[__I, __T]": ...

class AsyncCachedPropertyInstanceState(Generic[__T]):
    cache: Dict[FieldName, __T]
    locks: Dict[FieldName, Lock]

class AsyncCachedPropertyDescriptor(Generic[__I, __T]):
    field_name: FieldName
    _load_value: Callable[[__I], __T]
    _fget: Callable[[__I], __T]
    _fset: Optional[Callable]
    _fdel: Optional[Callable]
    def __init__(
        self, _fget: Callable[[__I], __T], _fset=None, _fdel=None, field_name=None
    ) -> None: ...
    def __set_name__(self, owner, name) -> None: ...
    def __get__(self, instance: __I, owner) -> ProxyType[__T]: ...
    def __set__(self, instance: __I, value): ...
    def __delete__(self, instance: __I) -> None: ...
    def setter(self, method): ...
    def deleter(self, method): ...
    def _check_method_name(self, method, method_type) -> None: ...
    def _check_method_sync(self, method, method_type) -> None: ...
    def get_instance_state(self, instance) -> AsyncCachedPropertyInstanceState[__T]: ...
    def get_lock(self, instance: __I) -> Lock: ...
    def get_cache(self, instance: __I) -> Dict[field_name, Any]:
        """Returns the in-memory cache dictionary for the given instance.

        This method retrieves the internal cache used to store computed property
        values for the instance. Each key in the returned dictionary is a FieldName,
        which is a type alias for str representing the property's field name, while
        the associated value is the cached result (of type Any) for that property.

        Example:
            >>> # Assume `some_obj` is an instance of a class using async_cached_property.
            >>> # And descriptor is the AsyncCachedPropertyDescriptor for that property.
            >>> cache_dict = descriptor.get_cache(some_obj)
            >>> # Each key in cache_dict is a FieldName (alias for str).
            >>> for key in cache_dict:
            ...     assert isinstance(key, str)

        See Also:
            :meth:`get_cache_value`, :meth:`set_cache_value`
        """
        ...
    def has_cache_value(self, instance: __I) -> bool: ...
    def get_cache_value(self, instance: __I) -> __T: ...
    def set_cache_value(self, instance: __I, value: __T) -> None: ...
    def del_cache_value(self, instance: __I) -> None: ...
    def get_loader(self, instance: __I) -> Callable[[], __T]: ...