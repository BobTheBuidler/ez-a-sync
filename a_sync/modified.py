
import functools
import inspect
import logging
import sys

from a_sync import _helpers, _kwargs
from a_sync._typing import *
from a_sync.modifiers.manager import ModifierManager

if TYPE_CHECKING:
    from a_sync import TaskMapping

logger = logging.getLogger(__name__)

class ModifiedMixin:
    modifiers: ModifierManager
    __slots__ = "modifiers", "wrapped"
    def _asyncify(self, func: SyncFn[P, T]) -> CoroFn[P, T]:
        """Applies only async modifiers."""
        coro_fn = _helpers._asyncify(func, self.modifiers.executor)
        return self.modifiers.apply_async_modifiers(coro_fn)
    @functools.cached_property
    def _await(self) -> Callable[[Awaitable[T]], T]:
        """Applies only sync modifiers."""
        return self.modifiers.apply_sync_modifiers(_helpers._await)
    @functools.cached_property
    def default(self) -> DefaultMode:
        return self.modifiers.default
    
        
class ASyncFunction(ModifiedMixin, Generic[P, T]):
    # NOTE: We can't use __slots__ here because it breaks functools.update_wrapper
    @overload
    def __init__(self, fn: CoroFn[P, T], **modifiers: Unpack[ModifierKwargs]) -> None:...
    @overload
    def __init__(self, fn: SyncFn[P, T], **modifiers: Unpack[ModifierKwargs]) -> None:...
    def __init__(self, fn: AnyFn[P, T], **modifiers: Unpack[ModifierKwargs]) -> None:
        _helpers._validate_wrapped_fn(fn)
        _check_not_genfunc(fn)
        self.modifiers = ModifierManager(modifiers)
        self.__wrapped__ = fn
        functools.update_wrapper(self, self.__wrapped__)
    
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
        logger.debug("calling %s fn: %s with args: %s kwargs: %s", self, self.fn, args, kwargs)
        return self.fn(*args, **kwargs)
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.__module__}.{self.__name__} at {hex(id(self))}>"
    
    @functools.cached_property
    def fn(self): # -> Union[SyncFn[[CoroFn[P, T]], MaybeAwaitable[T]], SyncFn[[SyncFn[P, T]], MaybeAwaitable[T]]]:
        """Returns the final wrapped version of 'self._fn' decorated with all of the a_sync goodness."""
        return self._async_wrap if self._async_def else self._sync_wrap
    
    def map(self, *iterables: AnyIterable[Any], concurrency: Optional[int] = None, task_name: str = "", **kwargs: P.kwargs) -> "TaskMapping[P, T]":
        from a_sync import TaskMapping
        return TaskMapping(self, *iterables, concurrency=concurrency, name=task_name, **kwargs)
    
    async def any(self, *iterables: AnyIterable[object], concurrency: Optional[int] = None, task_name: str = "", **kwargs: P.kwargs) -> bool:
        return await self.map(*iterables, concurrency=concurrency, task_name=task_name, **kwargs).any(pop=True, sync=False)
    
    async def all(self, *iterables: AnyIterable[object], concurrency: Optional[int] = None, task_name: str = "", **kwargs: P.kwargs) -> bool:
        return await self.map(*iterables, concurrency=concurrency, task_name=task_name, **kwargs).all(pop=True, sync=False)
    
    async def min(self, *iterables: AnyIterable[object], concurrency: Optional[int] = None, task_name: str = "", **kwargs: P.kwargs) -> T:
        return await self.map(*iterables, concurrency=concurrency, task_name=task_name, **kwargs).min(pop=True, sync=False)
    
    async def max(self, *iterables: AnyIterable[object], concurrency: Optional[int] = None, task_name: str = "", **kwargs: P.kwargs) -> T:
        return await self.map(*iterables, concurrency=concurrency, task_name=task_name, **kwargs).max(pop=True, sync=False)
    
    async def sum(self, *iterables: AnyIterable[object], concurrency: Optional[int] = None, task_name: str = "", **kwargs: P.kwargs) -> T:
        return await self.map(*iterables, concurrency=concurrency, task_name=task_name, **kwargs).sum(pop=True, sync=False)
    
    @functools.cached_property
    def _sync_default(self) -> bool:
        """If user did not specify a default, we defer to the function. 'def' vs 'async def'"""
        return True if self.default == 'sync' else False if self.default == 'async' else not self._async_def
    
    @property
    def _async_def(self) -> bool:
        return asyncio.iscoroutinefunction(self.__wrapped__)
    
    def _run_sync(self, kwargs: dict) -> bool:
        if flag := _kwargs.get_flag_name(kwargs):
            # If a flag was specified in the kwargs, we will defer to it.
            return _kwargs.is_sync(flag, kwargs, pop_flag=True)
        else:
            # No flag specified in the kwargs, we will defer to 'default'.
            return self._sync_default
    
    @functools.cached_property
    def _asyncified(self) -> CoroFn[P, T]:
        """Turns 'self._fn' async and applies both sync and async modifiers."""
        if self._async_def:
            raise TypeError(f"Can only be applied to sync functions, not {self.__wrapped__}")
        return self._asyncify(self._modified_fn)  # type: ignore [arg-type]
    
    @functools.cached_property
    def _modified_fn(self) -> AnyFn[P, T]:
        """
        Applies sync modifiers to 'self._fn' if 'self._fn' is a sync function.
        Applies async modifiers to 'self._fn' if 'self._fn' is a sync function.
        """
        if self._async_def:
            return self.modifiers.apply_async_modifiers(self.__wrapped__)  # type: ignore [arg-type]
        return self.modifiers.apply_sync_modifiers(self.__wrapped__)  # type: ignore [return-value]
    
    @functools.cached_property
    def _async_wrap(self): # -> SyncFn[[CoroFn[P, T]], MaybeAwaitable[T]]:
        """The final wrapper if self._fn is an async function."""
        @functools.wraps(self._modified_fn)
        def async_wrap(*args: P.args, **kwargs: P.kwargs) -> MaybeAwaitable[T]:  # type: ignore [name-defined]
            should_await = self._run_sync(kwargs) # Must take place before coro is created, we're popping a kwarg.
            coro = self._modified_fn(*args, **kwargs)
            return self._await(coro) if should_await else coro
        return async_wrap
    
    @functools.cached_property
    def _sync_wrap(self): # -> SyncFn[[SyncFn[P, T]], MaybeAwaitable[T]]:
        """The final wrapper if self._fn is a sync function."""
        @functools.wraps(self._modified_fn)
        def sync_wrap(*args: P.args, **kwargs: P.kwargs) -> MaybeAwaitable[T]:  # type: ignore [name-defined]
            if self._run_sync(kwargs):
                return self._modified_fn(*args, **kwargs)
            return self._asyncified(*args, **kwargs)            
        return sync_wrap

if sys.version_info < (3, 10):
    _inherit = ASyncFunction[AnyFn[P, T], ASyncFunction[P, T]]
else:
    _inherit = ASyncFunction[[AnyFn[P, T]], ASyncFunction[P, T]]
              
class ASyncDecorator(ModifiedMixin):
    def __init__(self, **modifiers: Unpack[ModifierKwargs]) -> None:
        assert 'default' in modifiers, modifiers
        self.modifiers = ModifierManager(modifiers)
        self.validate_inputs()
        
    def validate_inputs(self) -> None:
        if self.modifiers.default not in ['sync', 'async', None]:
            raise ValueError(f"'default' must be either 'sync', 'async', or None. You passed {self.modifiers.default}.")
        
    @overload
    def __call__(self, func: CoroFn[P, T]) -> ASyncFunction[P, T]:  # type: ignore [override]
        ...
    @overload
    def __call__(self, func: SyncFn[P, T]) -> ASyncFunction[P, T]:  # type: ignore [override]
        ...
    def __call__(self, func: AnyFn[P, T]) -> ASyncFunction[P, T]:  # type: ignore [override]
        if self.default == "async":
            return ASyncFunctionAsyncDefault(func, **self.modifiers)
        elif self.default == "sync":
            return ASyncFunctionSyncDefault(func, **self.modifiers)
        elif asyncio.iscoroutinefunction(func):
            return ASyncFunctionAsyncDefault(func, **self.modifiers)
        else:
            return ASyncFunctionSyncDefault(func, **self.modifiers)

def _check_not_genfunc(func: Callable) -> None:
    if inspect.isasyncgenfunction(func) or inspect.isgeneratorfunction(func):
        raise ValueError("unable to decorate generator functions with this decorator")


# Mypy helper classes

class ASyncFunctionSyncDefault(ASyncFunction[P, T]):
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
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> MaybeAwaitable[T]:
        return self.fn(*args, **kwargs)
    
class ASyncFunctionAsyncDefault(ASyncFunction[P, T]):
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
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> MaybeAwaitable[T]:
        return self.fn(*args, **kwargs)

class ASyncDecoratorSyncDefault(ASyncDecorator):
    @overload
    def __call__(self, func: AnyBoundMethod[P, T]) -> ASyncFunctionSyncDefault[P, T]:  # type: ignore [override]
        ...
    @overload
    def __call__(self, func: AnyFn[P, T]) -> ASyncFunctionSyncDefault[P, T]:  # type: ignore [override]
        ...
    def __call__(self, func: AnyFn[P, T]) -> ASyncFunctionSyncDefault[P, T]:
        return ASyncFunctionSyncDefault(func, **self.modifiers)

class ASyncDecoratorAsyncDefault(ASyncDecorator):
    @overload
    def __call__(self, func: AnyBoundMethod[P, T]) -> ASyncFunctionAsyncDefault[P, T]:  # type: ignore [override]
        ...
    @overload
    def __call__(self, func: AnyFn[P, T]) -> ASyncFunctionAsyncDefault[P, T]:  # type: ignore [override]
        ...
    def __call__(self, func: AnyFn[P, T]) -> ASyncFunctionAsyncDefault[P, T]:
        return ASyncFunctionAsyncDefault(func, **self.modifiers)
    