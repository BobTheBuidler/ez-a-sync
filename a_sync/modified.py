
import functools

from a_sync import _helpers, _kwargs, exceptions
from a_sync._typing import *
from a_sync.modifiers import ModifierManager
    

class Modified(Generic[T]):
    modifiers: ModifierManager
    def _asyncify(self, func: SyncFn[P, T]) -> CoroFn[P, T]:
        """Applies only async modifiers."""
        coro_fn = _helpers._asyncify(func, self.modifiers.executor)
        return self.modifiers.apply_async_modifiers(coro_fn)
    @functools.cached_property
    def _await(self): # -> SyncFn[[Awaitable[T]]] T]:
        """Applies only sync modifiers."""
        return self.modifiers.apply_sync_modifiers(_helpers._await)
    @property
    def default(self) -> DefaultMode:
        return self.modifiers.default
    
        
class ASyncFunction(Modified[T], Callable[P, T]):
    @overload
    def __init__(self, fn: CoroFn[P, T], **modifiers: Unpack[ModifierKwargs]) -> None:...
    @overload
    def __init__(self, fn: SyncFn[P, T], **modifiers: Unpack[ModifierKwargs]) -> None:...
    def __init__(self, fn: AnyFn[P, T], **modifiers: Unpack[ModifierKwargs]) -> None:
        _helpers._validate_wrapped_fn(fn)
        self.modifiers = ModifierManager(**modifiers)
        self._fn = fn
    
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> MaybeAwaitable[T]:
        return self.fn(*args, **kwargs)
    
    @functools.cached_property
    def fn(self): # -> Union[SyncFn[[CoroFn[P, T]], MaybeAwaitable[T]], SyncFn[[SyncFn[P, T]], MaybeAwaitable[T]]]:
        """Returns the final wrapped version of 'self._fn' decorated with all of the a_sync goodness."""
        return self._async_wrap if self._async_def else self._sync_wrap
    
    @property
    def _sync_default(self) -> bool:
        """If user did not specify a default, we defer to the function. 'def' vs 'async def'"""
        return True if self.default == 'sync' else False if self.default == 'async' else not self._async_def
    
    @property
    def _async_def(self) -> bool:
        return asyncio.iscoroutinefunction(self._fn)
    
    def _run_sync(self, kwargs: dict):
        try:
            # If a flag was specified in the kwargs, we will defer to it.
            return _kwargs.is_sync(kwargs, pop_flag=True)
        except exceptions.NoFlagsFound:
            # No flag specified in the kwargs, we will defer to 'default'.
            return self._sync_default
    
    @functools.cached_property
    def _asyncified(self) -> CoroFn[P, T]:
        """Turns 'self._fn' async and applies both sync and async modifiers."""
        assert not self._async_def, f"Can only be applied to sync functions, not {self._fn}"
        return self._asyncify(self._modified_fn)
    
    @functools.cached_property
    def _modified_fn(self) -> AnyFn[P, T]:
        """
        Applies sync modifiers to 'self._fn' if 'self._fn' is a sync function.
        Applies async modifiers to 'self._fn' if 'self._fn' is a sync function.
        """
        if self._async_def:
            return self.modifiers.apply_async_modifiers(self._fn)
        return self.modifiers.apply_sync_modifiers(self._fn)
    
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
              
class ASyncDecorator(ASyncFunction[AnyFn[P, T], ASyncFunction[P, T]]):
    _fn = None
    def __init__(self, **modifiers: Unpack[ModifierKwargs]) -> None:
        assert 'default' in modifiers, modifiers
        self.modifiers = ModifierManager(**modifiers)
        self.validate_inputs()
        
    def validate_inputs(self) -> None:
        if self.default not in ['sync', 'async', None]:
            raise ValueError(f"'default' must be either 'sync', 'async', or None. You passed {self.default}.")
        
    def __call__(self, func: AnyFn[P, T]) -> ASyncFunction[P, T]:
        return ASyncFunction(func, **self.modifiers)
