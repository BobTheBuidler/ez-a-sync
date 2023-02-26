
import functools
from inspect import isawaitable
from typing import Callable, TypeVar, overload, Awaitable

from typing_extensions import ParamSpec  # type: ignore

from a_sync import _helpers, _descriptors
from a_sync.decorator import a_sync as unbound_a_sync

P = ParamSpec("P")
T = TypeVar("T")


def a_sync(coro_fn: Callable[P, T]) -> Callable[P, T]:  # type: ignore
    # First we wrap the coro_fn so overriding kwargs are handled automagically.
    wrapped_coro_fn = unbound_a_sync(coro_fn)

    @functools.wraps(coro_fn)
    def bound_a_sync_wrap(self, *args: P.args, **kwargs: P.kwargs) -> T:  # type: ignore
        from a_sync.base import ASyncBase
        from a_sync._meta import ASyncMeta
        if not isinstance(self, ASyncBase) and not isinstance(self.__class__, ASyncMeta):
            raise RuntimeError(f"{self} must be an instance of a class that eiher inherits from ASyncBase or specifies ASyncMeta as its metaclass.")
        # This could either be a coroutine or a return value from an awaited coroutine,
        #   depending on if an overriding kwarg was passed into the function call.
        retval_or_coro = wrapped_coro_fn(self, *args, **kwargs)
        if not isawaitable(retval_or_coro):
            # The coroutine was already awaited due to the use of an overriding kwarg.
            # We can return the value.
            return retval_or_coro            
        # The awaitable was not awaited, so now we need to check the flag as defined on 'self' and await if appropriate.
        return _helpers._await_if_sync(retval_or_coro, self._should_await(kwargs))  # type: ignore
    return bound_a_sync_wrap


@overload
def a_sync_property(async_property: _descriptors.AsyncPropertyDescriptor) -> _descriptors.AsyncPropertyDescriptor:
    ...
@overload
def a_sync_property(async_property: _descriptors.AsyncCachedPropertyDescriptor) -> _descriptors.AsyncCachedPropertyDescriptor:  # type: ignore
    ...
def a_sync_property(async_property) -> tuple:
    if not isinstance(async_property, (_descriptors.AsyncPropertyDescriptor, _descriptors.AsyncCachedPropertyDescriptor)):
        raise TypeError(f"{async_property} must be one of: AsyncPropertyDescriptor, AsyncCachedPropertyDescriptor")

    from a_sync.base import ASyncBase
    from a_sync._meta import ASyncMeta

    async_property.hidden_method_name = f"__{async_property.field_name}"

    @functools.wraps(async_property)
    def a_sync_method(self, **kwargs):
        if not isinstance(self, ASyncBase) and not isinstance(self.__class__, ASyncMeta):
            raise RuntimeError(f"{self} must be an instance of a class that eiher inherits from ASyncBase or specifies ASyncMeta as its metaclass.")
        awaitable: Awaitable[T] = async_property.__get__(self, async_property)
        return _helpers._await_if_sync(awaitable, self._should_await(kwargs))  # type: ignore
    @property
    @functools.wraps(async_property)
    def a_sync_property(self) -> T:
        a_sync_method = getattr(self, async_property.hidden_method_name)
        return _helpers._await_if_sync(a_sync_method(sync=False), self._should_await({}))
    return a_sync_property, a_sync_method
