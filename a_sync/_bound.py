
import functools
from inspect import isawaitable
from typing import Awaitable, Callable, overload

from a_sync import _helpers
from a_sync._typing import *
from a_sync.decorator import a_sync as unbound_a_sync
from a_sync.property import (AsyncCachedPropertyDescriptor,
                             AsyncPropertyDescriptor)


def _wrap_bound_method(coro_fn: Callable[P, T], **modifiers: ModifierKwargs) -> Callable[P, T]:  # type: ignore [misc]
    from a_sync.abstract import ASyncABC

    # First we wrap the coro_fn so overriding kwargs are handled automagically.
    wrapped_coro_fn = unbound_a_sync(coro_fn=coro_fn, **modifiers)

    @functools.wraps(coro_fn)
    def bound_a_sync_wrap(self, *args: P.args, **kwargs: P.kwargs) -> T:  # type: ignore [name-defined]
        if not isinstance(self, ASyncABC):
            raise RuntimeError(f"{self} must be an instance of a class that inherits from ASyncABC.")
        # This could either be a coroutine or a return value from an awaited coroutine,
        #   depending on if an overriding kwarg was passed into the function call.
        retval = coro = wrapped_coro_fn(self, *args, **kwargs)
        if not isawaitable(retval):
            # The coroutine was already awaited due to the use of an overriding kwarg.
            # We can return the value.
            return retval           
        # The awaitable was not awaited, so now we need to check the flag as defined on 'self' and await if appropriate.
        return _helpers._await(coro) if self.__a_sync_should_await__(kwargs) else coro  # type: ignore [call-overload]
    return bound_a_sync_wrap


@overload
def _wrap_property(async_property: AsyncPropertyDescriptor, **modifiers: ModifierKwargs) -> AsyncPropertyDescriptor:
    ...
@overload
def _wrap_property(async_property: AsyncCachedPropertyDescriptor, **modifiers: ModifierKwargs) -> AsyncCachedPropertyDescriptor:  # type: ignore [misc]
    ...
def _wrap_property(async_property, **modifiers: ModifierKwargs) -> tuple:
    if not isinstance(async_property, (AsyncPropertyDescriptor, AsyncCachedPropertyDescriptor)):
        raise TypeError(f"{async_property} must be one of: AsyncPropertyDescriptor, AsyncCachedPropertyDescriptor")

    from a_sync.abstract import ASyncABC

    async_property.hidden_method_name = f"__{async_property.field_name}__"
    
    @unbound_a_sync(**modifiers)
    async def awaitable(instance: ASyncABC) -> Awaitable[T]:
        return await async_property.__get__(instance, async_property)
    
    @functools.wraps(async_property)
    def a_sync_method(self: ASyncABC, **kwargs) -> T:
        if not isinstance(self, ASyncABC):
            raise RuntimeError(f"{self} must be an instance of a class that inherits from ASyncABC.")
        return _helpers._await(awaitable(self)) if self.__a_sync_should_await__(kwargs) else awaitable(self)
    
    @property  # type: ignore [misc]
    @functools.wraps(async_property)
    def a_sync_property(self: ASyncABC) -> T:
        coro = getattr(self, async_property.hidden_method_name)(sync=False)
        return _helpers._await(coro) if self.__a_sync_should_await__({}) else coro
    
    return a_sync_property, a_sync_method
