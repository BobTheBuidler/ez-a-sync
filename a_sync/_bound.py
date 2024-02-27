# mypy: disable-error-code=valid-type
# mypy: disable-error-code=misc
import functools
from inspect import isawaitable

from a_sync import _helpers
from a_sync._descriptor import ASyncDescriptor
from a_sync._typing import *
from a_sync.modified import ASyncFunction, ASyncFunctionAsyncDefault, ASyncFunctionSyncDefault

if TYPE_CHECKING:
    from a_sync.abstract import ASyncABC

class ASyncMethodDescriptor(ASyncDescriptor[ASyncFunction[P, T]], Generic[O, P, T]):
    _fget: ASyncFunction[Concatenate[O, P], T]
    def __get__(self, instance: ASyncInstance, owner) -> "ASyncBoundMethod[P, T]":
        if instance is None:
            return self
        try:
            return instance.__dict__[self.field_name]
        except KeyError:
            from a_sync.abstract import ASyncABC
            if self.default == "sync":
                bound = ASyncBoundMethodSyncDefault(instance, self._fget, **self.modifiers)
            elif self.default == "async":
                bound = ASyncBoundMethodAsyncDefault(instance, self._fget, **self.modifiers)
            elif isinstance(instance, ASyncABC) and instance.__a_sync_default_mode__() == "sync":
                bound = ASyncBoundMethodSyncDefault(instance, self._fget, **self.modifiers)
            elif isinstance(instance, ASyncABC) and instance.__a_sync_default_mode__() == "async":
                bound = ASyncBoundMethodAsyncDefault(instance, self._fget, **self.modifiers)
            else:
                bound = ASyncBoundMethod(instance, self._fget, **self.modifiers)
            instance.__dict__[self.field_name] = bound
            return bound

class ASyncMethodDescriptorSyncDefault(ASyncMethodDescriptor[ASyncInstance, P, T]):
    def __get__(self, instance: ASyncInstance, owner) -> "ASyncBoundMethodSyncDefault[P, T]":
        return super().__get__(instance, owner)

class ASyncMethodDescriptorAsyncDefault(ASyncMethodDescriptor[ASyncInstance, P, T]):
    def __get__(self, instance: ASyncInstance, owner) -> "ASyncBoundMethodAsyncDefault[P, T]":
        return super().__get__(instance, owner)

class ASyncBoundMethod(ASyncFunction[P, T]):
    @overload
    def wrap(
        cls,
        a_sync_fn: ASyncFunction[Concatenate[ASyncInstance, P], T], 
        instance: "ASyncABC", 
        force_await: Literal[True], 
        *args: P.args, 
        **kwargs: P.kwargs,
    ) -> T:...
    @classmethod
    def wrap(
        cls,
        a_sync_fn: ASyncFunction[Concatenate[ASyncInstance, P], T], 
        instance: "ASyncABC", 
        force_await: bool, 
        *args: P.args, 
        **kwargs: P.kwargs,
    ) -> Union[T, Awaitable[T]]:
        # This could either be a coroutine or a return value from an awaited coroutine,
        #   depending on if an overriding flag kwarg was passed into the function call.
        retval = coro = a_sync_fn(instance, *args, **kwargs)
        if not isawaitable(retval):
            # The coroutine was already awaited due to the use of an overriding flag kwarg.
            # We can return the value.
            return retval  # type: ignore [return-value]
        # The awaitable was not awaited, so now we need to check the flag as defined on 'self' and await if appropriate.
        return _helpers._await(coro) if instance.__a_sync_should_await__(kwargs, force=force_await) else coro  # type: ignore [call-overload, return-value]
    def __init__(self, instance: ASyncInstance, unbound: AnyFn[Concatenate[ASyncInstance, P], T], **modifiers: Unpack[ModifierKwargs]) -> None:
        from a_sync.abstract import ASyncABC
        if not isinstance(instance, ASyncABC):
            raise RuntimeError(f"{instance} must be an instance of a class that inherits from ASyncABC.")
        self.instance = instance

        # First we unwrap the coro_fn and rewrap it so overriding flag kwargs are handled automagically.
        if isinstance(unbound, ASyncFunction):
            unbound = unbound.__wrapped__
        
        modifiers, self.force_await = _clean_default_from_modifiers(unbound, modifiers)
        modified = _a_sync_function_cache(unbound, **modifiers)
        wrapped = functools.partial(ASyncBoundMethod.wrap, modified, self.instance, self.force_await)
        functools.update_wrapper(wrapped, unbound)
        super().__init__(wrapped, **modifiers)
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} for function {self.__module__}.{self.instance.__class__.__name__}.{self.__name__} bound to {self.instance}>"


class ASyncBoundMethodSyncDefault(ASyncBoundMethod[P, T]):
    def __get__(self, instance: ASyncInstance, owner) -> ASyncFunctionSyncDefault[P, T]:
        return super().__get__(instance, owner)

class ASyncBoundMethodAsyncDefault(ASyncBoundMethod[P, T]):
    def __get__(self, instance: ASyncInstance, owner) -> ASyncFunctionAsyncDefault[P, T]:
        return super().__get__(instance, owner)


@functools.lru_cache(maxsize=None)
def _a_sync_function_cache(unbound: CoroFn[P, T], **modifiers: Unpack[ModifierKwargs]) -> ASyncFunction[P, T]:
    return ASyncFunction(unbound, **modifiers)

def _clean_default_from_modifiers(
    coro_fn: CoroFn[P, T],  # type: ignore [misc]
    modifiers: ModifierKwargs,
):
    # NOTE: We set the default here manually because the default set by the user will be used later in the code to determine whether to await.
    force_await = None
    if not asyncio.iscoroutinefunction(coro_fn) and not isinstance(coro_fn, ASyncFunction):
        if 'default' not in modifiers or modifiers['default'] != 'async':
            if 'default' in modifiers and modifiers['default'] == 'sync':
                force_await = True
            modifiers['default'] = 'async'
    return modifiers, force_await
