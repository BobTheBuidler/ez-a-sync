
import functools
from inspect import isawaitable

from a_sync import _helpers
from a_sync._typing import *
from a_sync.decorator import a_sync as unbound_a_sync
from a_sync.modified import ASyncFunction
from a_sync.property import (AsyncCachedPropertyDescriptor,
                             AsyncPropertyDescriptor)

if TYPE_CHECKING:
    from a_sync.abstract import ASyncABC


def _wrap_bound_method(
    coro_fn: AsyncBoundMethod[P, T],
    **modifiers: Unpack[ModifierKwargs]
) -> AsyncBoundMethod[P, T]:  # type: ignore [misc]
    from a_sync.abstract import ASyncABC

    # First we wrap the coro_fn so overriding kwargs are handled automagically.
    # NOTE: We set the default here manually because the default set by the user will be used later in the code to determine whether to await.
    _force_await = None
    if not asyncio.iscoroutinefunction(coro_fn) and not isinstance(coro_fn, ASyncFunction):
        if 'default' not in modifiers or modifiers['default'] is not 'async':
            if 'default' in modifiers and modifiers['default'] == 'sync':
                _force_await = True
            modifiers['default'] = 'async'
        
    wrapped_coro_fn: AsyncBoundMethod[P, T] = unbound_a_sync(coro_fn=coro_fn, **modifiers)  # type: ignore [arg-type]

    @functools.wraps(coro_fn)
    def bound_a_sync_wrap(self: ASyncABC, *args: P.args, **kwargs: P.kwargs) -> T:  # type: ignore [name-defined]
        if not isinstance(self, ASyncABC):
            raise RuntimeError(f"{self} must be an instance of a class that inherits from ASyncABC.")
        # This could either be a coroutine or a return value from an awaited coroutine,
        #   depending on if an overriding kwarg was passed into the function call.
        retval = coro = wrapped_coro_fn(self, *args, **kwargs)
        if not isawaitable(retval):
            # The coroutine was already awaited due to the use of an overriding kwarg.
            # We can return the value.
            return retval  # type: ignore [return-value]
        # The awaitable was not awaited, so now we need to check the flag as defined on 'self' and await if appropriate.
        return _helpers._await(coro) if self.__a_sync_should_await__(kwargs, force=_force_await) else coro  # type: ignore [call-overload, return-value]
    return bound_a_sync_wrap


@overload
def _wrap_property(
    async_property: AsyncPropertyDescriptor[T],
    **modifiers: Unpack[ModifierKwargs]
) -> AsyncPropertyDescriptor[T]:...

@overload
def _wrap_property(
    async_property: AsyncCachedPropertyDescriptor[T],
    **modifiers: Unpack[ModifierKwargs]
) -> AsyncCachedPropertyDescriptor:...

def _wrap_property(
    async_property: Union[AsyncPropertyDescriptor[T], AsyncCachedPropertyDescriptor[T]],
    **modifiers: Unpack[ModifierKwargs]
) -> Tuple[Property[T], HiddenMethod[T]]:
    if not isinstance(async_property, (AsyncPropertyDescriptor, AsyncCachedPropertyDescriptor)):
        raise TypeError(f"{async_property} must be one of: AsyncPropertyDescriptor, AsyncCachedPropertyDescriptor")

    from a_sync.abstract import ASyncABC

    async_property.hidden_method_name = f"__{async_property.field_name}__"
    
    @functools.wraps(async_property)
    def a_sync_method(self: ASyncABC, **kwargs) -> T:
        if not isinstance(self, ASyncABC):
            raise RuntimeError(f"{self} must be an instance of a class that inherits from ASyncABC.")
        awaitable = async_property.__get__(self, async_property)
        return _helpers._await(awaitable) if self.__a_sync_should_await__(kwargs) else awaitable
    
    @property  # type: ignore [misc]
    @functools.wraps(async_property)
    def a_sync_property(self: ASyncABC) -> T:
        coro = getattr(self, async_property.hidden_method_name)(sync=False)
        return _helpers._await(coro) if self.__a_sync_should_await__({}) else coro
    
    return a_sync_property, a_sync_method
