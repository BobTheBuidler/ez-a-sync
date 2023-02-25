
import functools
from inspect import isawaitable
from typing import Any, Callable, TypeVar, Union, overload, Awaitable

from async_property.base import AsyncPropertyDescriptor
from async_property.cached import AsyncCachedPropertyDescriptor
from typing_extensions import ParamSpec  # type: ignore

from a_sync import _helpers
from a_sync.decorator import a_sync as unbound_a_sync

P = ParamSpec("P")
T = TypeVar("T")


def a_sync(coro_fn: Callable[P, T]) -> Callable[P, T]:  # type: ignore
    # First we wrap the coro_fn so overriding kwargs are handled automagically.
    wrapped_coro_fn = unbound_a_sync(coro_fn)

    @functools.wraps(coro_fn)
    def bound_a_sync_wrap(self, *args: P.args, **kwargs: P.kwargs) -> T:  # type: ignore
        from a_sync.base import ASyncBase
        if not isinstance(self, ASyncBase):
            raise RuntimeError(f"{self} must be an instance of a class that inherits from ASyncBase")
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
def a_sync_property(async_property: AsyncPropertyDescriptor) -> AsyncPropertyDescriptor:
    ...
@overload
def a_sync_property(async_property: AsyncCachedPropertyDescriptor) -> AsyncCachedPropertyDescriptor:  # type: ignore
    ...
def a_sync_property(async_property):
    if not isinstance(async_property, (AsyncPropertyDescriptor, AsyncCachedPropertyDescriptor)):
        raise TypeError(f"{async_property} must be one of: AsyncPropertyDescriptor, AsyncCachedPropertyDescriptor")
    
    from a_sync.base import ASyncBase

    @property
    @functools.wraps(async_property)
    def a_sync_property_wrap(self) -> T:
        if not isinstance(self, ASyncBase):
            raise RuntimeError(f"{self} must be an instance of a class that inherits from ASyncBase")
        awaitable: Awaitable[T] = async_property.__get__(self, async_property)
        return _helpers._await_if_sync(awaitable, self._should_await({}))  # type: ignore
    return a_sync_property_wrap
