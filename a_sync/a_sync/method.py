# mypy: disable-error-code=valid-type
# mypy: disable-error-code=misc
import functools
import logging
import weakref
from inspect import isawaitable

from a_sync._typing import *
from a_sync.a_sync import _helpers, _kwargs
from a_sync.a_sync._descriptor import ASyncDescriptor
from a_sync.a_sync.function import ASyncFunction, ASyncFunctionAsyncDefault, ASyncFunctionSyncDefault

if TYPE_CHECKING:
    from a_sync import TaskMapping
    from a_sync.a_sync.abstract import ASyncABC

logger = logging.getLogger(__name__)

class ASyncMethodDescriptor(ASyncDescriptor[I, P, T]):
    __wrapped__: AnyFn[P, T]
    async def __call__(self, instance: I, *args: P.args, **kwargs: P.kwargs) -> T:
        # NOTE: This is only used by TaskMapping atm  # TODO: use it elsewhere
        logger.debug("awaiting %s for instance: %s args: %s kwargs: %s", self, instance, args, kwargs)
        return await self.__get__(instance, None)(*args, **kwargs)
    @overload
    def __get__(self, instance: None, owner: Type[I]) -> Self:...
    @overload
    def __get__(self, instance: I, owner: Type[I]) -> "ASyncBoundMethod[I, P, T]":...
    def __get__(self, instance: Optional[I], owner: Type[I]) -> Union[Self, "ASyncBoundMethod[I, P, T]"]:
        if instance is None:
            return self
        try:
            bound = instance.__dict__[self.field_name]
            # we will set a new one in the finally block
            bound._cache_handle.cancel()
        except KeyError:
            from a_sync.a_sync.abstract import ASyncABC
            if self.default == "sync":
                bound = ASyncBoundMethodSyncDefault(instance, self.__wrapped__, self.__is_async_def__, **self.modifiers)
            elif self.default == "async":
                bound = ASyncBoundMethodAsyncDefault(instance, self.__wrapped__, self.__is_async_def__, **self.modifiers)
            elif isinstance(instance, ASyncABC):
                try:
                    if instance.__a_sync_instance_should_await__:
                        bound = ASyncBoundMethodSyncDefault(instance, self.__wrapped__, self.__is_async_def__, **self.modifiers)
                    else:
                        bound = ASyncBoundMethodAsyncDefault(instance, self.__wrapped__, self.__is_async_def__, **self.modifiers)
                except AttributeError:
                    bound = ASyncBoundMethod(instance, self.__wrapped__, self.__is_async_def__, **self.modifiers)
            else:
                bound = ASyncBoundMethod(instance, self.__wrapped__, self.__is_async_def__, **self.modifiers)
            instance.__dict__[self.field_name] = bound
            logger.debug("new bound method: %s", bound)
        # Handler for popping unused bound methods from bound method cache
        bound._cache_handle = self._get_cache_handle(instance)
        return bound
    def __set__(self, instance, value):
        raise RuntimeError(f"cannot set {self.field_name}, {self} is what you get. sorry.")
    def __delete__(self, instance):
        raise RuntimeError(f"cannot delete {self.field_name}, you're stuck with {self} forever. sorry.")
    @functools.cached_property
    def __is_async_def__(self) -> bool:
        return asyncio.iscoroutinefunction(self.__wrapped__)
    def _get_cache_handle(self, instance: I) -> asyncio.TimerHandle:
        # NOTE: use `instance.__dict__.pop` instead of `delattr` so we don't create a strong ref to `instance`
        return asyncio.get_event_loop().call_later(300, instance.__dict__.pop, self.field_name)

@final
class ASyncMethodDescriptorSyncDefault(ASyncMethodDescriptor[I, P, T]):
    default = "sync"
    any: ASyncFunctionSyncDefault[Concatenate[AnyIterable[I], P], bool]
    all: ASyncFunctionSyncDefault[Concatenate[AnyIterable[I], P], bool]
    min: ASyncFunctionSyncDefault[Concatenate[AnyIterable[I], P], T]
    max: ASyncFunctionSyncDefault[Concatenate[AnyIterable[I], P], T]
    sum: ASyncFunctionSyncDefault[Concatenate[AnyIterable[I], P], T]
    @overload
    def __get__(self, instance: None, owner: Type[I] = None) -> "ASyncMethodDescriptorSyncDefault[I, P, T]":...
    @overload
    def __get__(self, instance: I, owner: Type[I] = None) -> "ASyncBoundMethodSyncDefault[I, P, T]":...
    def __get__(self, instance: Optional[I], owner: Type[I] = None) -> "Union[ASyncMethodDescriptorSyncDefault, ASyncBoundMethodSyncDefault[I, P, T]]":
        if instance is None:
            return self
        try:
            bound = instance.__dict__[self.field_name]
            # we will set a new one in the finally block
            bound._cache_handle.cancel()
        except KeyError:
            bound = ASyncBoundMethodSyncDefault(instance, self.__wrapped__, self.__is_async_def__, **self.modifiers)
            instance.__dict__[self.field_name] = bound
            logger.debug("new bound method: %s", bound)
        # Handler for popping unused bound methods from bound method cache
        bound._cache_handle = self._get_cache_handle(instance)
        return bound

@final
class ASyncMethodDescriptorAsyncDefault(ASyncMethodDescriptor[I, P, T]):
    default = "async"
    any: ASyncFunctionAsyncDefault[Concatenate[AnyIterable[I], P], bool]
    all: ASyncFunctionAsyncDefault[Concatenate[AnyIterable[I], P], bool]
    min: ASyncFunctionAsyncDefault[Concatenate[AnyIterable[I], P], T]
    max: ASyncFunctionAsyncDefault[Concatenate[AnyIterable[I], P], T]
    sum: ASyncFunctionAsyncDefault[Concatenate[AnyIterable[I], P], T]
    @overload
    def __get__(self, instance: None, owner: Type[I]) -> "ASyncMethodDescriptorAsyncDefault[I, P, T]":...
    @overload
    def __get__(self, instance: I, owner: Type[I]) -> "ASyncBoundMethodAsyncDefault[I, P, T]":...
    def __get__(self, instance: Optional[I], owner: Type[I]) -> "Union[ASyncMethodDescriptorAsyncDefault, ASyncBoundMethodAsyncDefault[I, P, T]]":
        if instance is None:
            return self
        try:
            bound = instance.__dict__[self.field_name]
            # we will set a new one in the finally block
            bound._cache_handle.cancel()
        except KeyError:
            bound = ASyncBoundMethodAsyncDefault(instance, self.__wrapped__, self.__is_async_def__, **self.modifiers)
            instance.__dict__[self.field_name] = bound
            logger.debug("new bound method: %s", bound)
        # Handler for popping unused bound methods from bound method cache
        bound._cache_handle = self._get_cache_handle(instance)
        return bound

class ASyncBoundMethod(ASyncFunction[P, T], Generic[I, P, T]):
    # NOTE: this is created by the Descriptor
    _cache_handle: asyncio.TimerHandle
    "An asyncio handle used to pop the bound method from `instance.__dict__` 5 minutes after its last use."

    __weakself__: "weakref.ref[I]"
    "A weak reference to the instance the function is bound to."

    __slots__ = "_is_async_def", "__weakself__"
    def __init__(
        self, 
        instance: I, 
        unbound: AnyFn[Concatenate[I, P], T], 
        async_def: bool,
        **modifiers: Unpack[ModifierKwargs],
    ) -> None:
        self.__weakself__ = weakref.ref(instance, self.__cancel_cache_handle)
        # First we unwrap the coro_fn and rewrap it so overriding flag kwargs are handled automagically.
        if isinstance(unbound, ASyncFunction):
            modifiers.update(unbound.modifiers)
            unbound = unbound.__wrapped__
        ASyncFunction.__init__(self, unbound, **modifiers)
        self._is_async_def = async_def
        "True if `self.__wrapped__` is a coroutine function, False otherwise."
        functools.update_wrapper(self, unbound)
    def __repr__(self) -> str:
        try:
            instance_type = type(self.__self__)
            return f"<{self.__class__.__name__} for function {instance_type.__module__}.{instance_type.__name__}.{self.__name__} bound to {self.__self__}>"
        except ReferenceError:
            return f"<{self.__class__.__name__} for function COLLECTED.COLLECTED.{self.__name__} bound to {self.__weakself__}>"
    @overload
    def __call__(self, *args: P.args, sync: Literal[True], **kwargs: P.kwargs) -> T:...
    @overload
    def __call__(self, *args: P.args, sync: Literal[False], **kwargs: P.kwargs) -> Awaitable[T]:...
    @overload
    def __call__(self, *args: P.args, asynchronous: Literal[False], **kwargs: P.kwargs) -> T:...
    @overload
    def __call__(self, *args: P.args, asynchronous: Literal[True], **kwargs: P.kwargs) -> Awaitable[T]:...
    @overload
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> MaybeAwaitable[T]:...
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> MaybeAwaitable[T]:
        logger.debug("calling %s with args: %s kwargs: %s", self, args, kwargs)
        # This could either be a coroutine or a return value from an awaited coroutine,
        #   depending on if an overriding flag kwarg was passed into the function call.
        retval = coro = ASyncFunction.__call__(self, self.__self__, *args, **kwargs)
        if not isawaitable(retval):
            # The coroutine was already awaited due to the use of an overriding flag kwarg.
            # We can return the value.
            pass
        elif self._should_await(kwargs):
            # The awaitable was not awaited, so now we need to check the flag as defined on 'self' and await if appropriate.
            logger.debug("awaiting %s for %s args: %s kwargs: %s", coro, self, args, kwargs)
            retval = _helpers._await(coro)
        logger.debug("returning %s for %s args: %s kwargs: %s", retval, self, args, kwargs)
        return retval  # type: ignore [call-overload, return-value]
    @property
    def __self__(self) -> I:
        "The instance the function is bound to."
        instance = self.__weakself__()
        if instance is not None:
            return instance
        raise ReferenceError(self)
    @functools.cached_property
    def __bound_to_a_sync_instance__(self) -> bool:
        from a_sync.a_sync.abstract import ASyncABC
        return isinstance(self.__self__, ASyncABC)
    def map(self, *iterables: AnyIterable[I], concurrency: Optional[int] = None, task_name: str = "", **kwargs: P.kwargs) -> "TaskMapping[I, T]":
        from a_sync import TaskMapping
        return TaskMapping(self, *iterables, concurrency=concurrency, name=task_name, **kwargs)
    async def any(self, *iterables: AnyIterable[I], concurrency: Optional[int] = None, task_name: str = "", **kwargs: P.kwargs) -> bool:
        return await self.map(*iterables, concurrency=concurrency, task_name=task_name, **kwargs).any(pop=True, sync=False)
    async def all(self, *iterables: AnyIterable[I], concurrency: Optional[int] = None, task_name: str = "", **kwargs: P.kwargs) -> bool:
        return await self.map(*iterables, concurrency=concurrency, task_name=task_name, **kwargs).all(pop=True, sync=False)
    async def min(self, *iterables: AnyIterable[I], concurrency: Optional[int] = None, task_name: str = "", **kwargs: P.kwargs) -> T:
        return await self.map(*iterables, concurrency=concurrency, task_name=task_name, **kwargs).min(pop=True, sync=False)
    async def max(self, *iterables: AnyIterable[I], concurrency: Optional[int] = None, task_name: str = "", **kwargs: P.kwargs) -> T:
        return await self.map(*iterables, concurrency=concurrency, task_name=task_name, **kwargs).max(pop=True, sync=False)
    async def sum(self, *iterables: AnyIterable[I], concurrency: Optional[int] = None, task_name: str = "", **kwargs: P.kwargs) -> T:
        return await self.map(*iterables, concurrency=concurrency, task_name=task_name, **kwargs).sum(pop=True, sync=False)
    def _should_await(self, kwargs: dict) -> bool:
        if flag := _kwargs.get_flag_name(kwargs):
            return _kwargs.is_sync(flag, kwargs, pop_flag=True)  # type: ignore [arg-type]
        elif self.default:
            return self.default == "sync"
        elif self.__bound_to_a_sync_instance__:
            self.__self__: "ASyncABC"
            return self.__self__.__a_sync_should_await__(kwargs)
        return self._is_async_def
    def __cancel_cache_handle(self, instance: I) -> None:
        cache_handle: asyncio.TimerHandle = self._cache_handle
        cache_handle.cancel()


class ASyncBoundMethodSyncDefault(ASyncBoundMethod[I, P, T]):
    def __get__(self, instance: Optional[I], owner: Type[I]) -> ASyncFunctionSyncDefault[P, T]:
        return ASyncBoundMethod.__get__(self, instance, owner)
    @overload
    def __call__(self, *args: P.args, sync: Literal[True], **kwargs: P.kwargs) -> T:...
    @overload
    def __call__(self, *args: P.args, sync: Literal[False], **kwargs: P.kwargs) -> Awaitable[T]:...
    @overload
    def __call__(self, *args: P.args, asynchronous: Literal[False], **kwargs: P.kwargs) -> T:...
    @overload
    def __call__(self, *args: P.args, asynchronous: Literal[True], **kwargs: P.kwargs) -> Awaitable[T]:...
    @overload
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:...
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        return ASyncBoundMethod.__call__(self, *args, **kwargs)

class ASyncBoundMethodAsyncDefault(ASyncBoundMethod[I, P, T]):
    def __get__(self, instance: I, owner: Type[I]) -> ASyncFunctionAsyncDefault[P, T]:
        return ASyncBoundMethod.__get__(self, instance, owner)
    @overload
    def __call__(self, *args: P.args, sync: Literal[True], **kwargs: P.kwargs) -> T:...
    @overload
    def __call__(self, *args: P.args, sync: Literal[False], **kwargs: P.kwargs) -> Awaitable[T]:...
    @overload
    def __call__(self, *args: P.args, asynchronous: Literal[False], **kwargs: P.kwargs) -> T:...
    @overload
    def __call__(self, *args: P.args, asynchronous: Literal[True], **kwargs: P.kwargs) -> Awaitable[T]:...
    @overload
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Awaitable[T]:...
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Awaitable[T]:
        return ASyncBoundMethod.__call__(self, *args, **kwargs)
