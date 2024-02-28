# mypy: disable-error-code=valid-type
# mypy: disable-error-code=misc
import functools
import logging
from inspect import isawaitable

from a_sync import _helpers, _kwargs
from a_sync._descriptor import ASyncDescriptor
from a_sync._typing import *
from a_sync.modified import ASyncFunction, ASyncFunctionAsyncDefault, ASyncFunctionSyncDefault


logger = logging.getLogger(__name__)

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
            elif isinstance(instance, ASyncABC) and instance.__a_sync_instance_should_await__:
                bound = ASyncBoundMethodSyncDefault(instance, self._fget, **self.modifiers)
            elif isinstance(instance, ASyncABC) and instance.__a_sync_instance_should_await__:
                bound = ASyncBoundMethodAsyncDefault(instance, self._fget, **self.modifiers)
            else:
                bound = ASyncBoundMethod(instance, self._fget, **self.modifiers)
            instance.__dict__[self.field_name] = bound
            logger.debug("new bound method: %s", bound)
            return bound
    def __set__(self, instance, value):
        raise RuntimeError(f"cannot set {self.field_name}, {self} is what you get. sorry.")
    def __delete__(self, instance):
        raise RuntimeError(f"cannot delete {self.field_name}, you're stuck with {self} forever. sorry.")

class ASyncMethodDescriptorSyncDefault(ASyncMethodDescriptor[ASyncInstance, P, T]):
    def __get__(self, instance: ASyncInstance, owner) -> "ASyncBoundMethodSyncDefault[P, T]":
        if instance is None:
            return self
        try:
            return instance.__dict__[self.field_name]
        except KeyError:
            bound = ASyncBoundMethodSyncDefault(instance, self._fget, **self.modifiers)
            instance.__dict__[self.field_name] = bound
            logger.debug("new bound method: %s", bound)
            return bound

class ASyncMethodDescriptorAsyncDefault(ASyncMethodDescriptor[ASyncInstance, P, T]):
    def __get__(self, instance: ASyncInstance, owner) -> "ASyncBoundMethodAsyncDefault[P, T]":
        if instance is None:
            return self
        try:
            return instance.__dict__[self.field_name]
        except KeyError:
            bound = ASyncBoundMethodAsyncDefault(instance, self._fget, **self.modifiers)
            instance.__dict__[self.field_name] = bound
            logger.debug("new bound method: %s", bound)
            return bound

class ASyncBoundMethod(ASyncFunction[P, T]):
    __slots__ = "instance", 
    def __init__(
        self, 
        instance: ASyncInstance, 
        unbound: AnyFn[Concatenate[ASyncInstance, P], T], 
        **modifiers: Unpack[ModifierKwargs],
    ) -> None:
        self.instance = instance
        # First we unwrap the coro_fn and rewrap it so overriding flag kwargs are handled automagically.
        if isinstance(unbound, ASyncFunction):
            modifiers.update(unbound.modifiers)
            unbound = unbound.__wrapped__
        if asyncio.iscoroutinefunction(unbound):
            async def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
                return await unbound(self.instance, *args, **kwargs)
        else:
            def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
                return unbound(self.instance, *args, **kwargs)
        functools.update_wrapper(wrapped, unbound)
        super().__init__(wrapped, **modifiers)
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} for function {self.__module__}.{self.instance.__class__.__name__}.{self.__name__} bound to {self.instance}>"
    def __call__(self, *args, **kwargs):
        logger.debug("calling %s", self)
        # This could either be a coroutine or a return value from an awaited coroutine,
        #   depending on if an overriding flag kwarg was passed into the function call.
        retval = coro = super().__call__(*args, **kwargs)
        if not isawaitable(retval):
            # The coroutine was already awaited due to the use of an overriding flag kwarg.
            # We can return the value.
            return retval  # type: ignore [return-value]
        # The awaitable was not awaited, so now we need to check the flag as defined on 'self' and await if appropriate.
        return _helpers._await(coro) if self.should_await(kwargs) else coro  # type: ignore [call-overload, return-value]
    @functools.cached_property
    def __bound_to_a_sync_instance__(self) -> bool:
        from a_sync.abstract import ASyncABC
        return isinstance(self.instance, ASyncABC)
    def should_await(self, kwargs: dict) -> bool:
        if flag := _kwargs.get_flag_name(kwargs):
            return _kwargs.is_sync(flag, kwargs, pop_flag=True)  # type: ignore [arg-type]
        elif self.default:
            return self.default == "sync"
        elif self.__bound_to_a_sync_instance__:
            return self.instance.__a_sync_should_await__(kwargs)
        return asyncio.iscoroutinefunction(self.__wrapped__)


class ASyncBoundMethodSyncDefault(ASyncBoundMethod[P, T]):
    def __get__(self, instance: ASyncInstance, owner) -> ASyncFunctionSyncDefault[P, T]:
        return super().__get__(instance, owner)
    def __call__(self, *args, **kwargs) -> T:
        return super().__call__(*args, **kwargs)

class ASyncBoundMethodAsyncDefault(ASyncBoundMethod[P, T]):
    def __get__(self, instance: ASyncInstance, owner) -> ASyncFunctionAsyncDefault[P, T]:
        return super().__get__(instance, owner)
    def __call__(self, *args, **kwargs) -> Awaitable[T]:
        return super().__call__(*args, **kwargs)
