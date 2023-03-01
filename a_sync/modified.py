
import functools

from a_sync import _helpers, _kwargs, exceptions
from a_sync._typing import *
from a_sync.modifiers import ModifierManager
    

class ASyncDecorator(Modified[T]):
    def __init__(self, modifiers: ModifierManager, default=None) -> None:
        self.default = default
        self.modifiers = modifiers
        self.validate_inputs()
    def __call__(self, func):
        return ASyncFunction(func, self.modifiers, self.default)
    def validate_inputs(self) -> None:
        if self.default not in ['sync', 'async', None]:
            raise ValueError(f"'default' must be either 'sync', 'async', or None. You passed {self.default}.")
        if not isinstance(self.modifiers, ModifierManager):
            raise TypeError(f"'modifiers should be of type 'ModifierManager'. You passed {self.modifiers}")

         
class ASyncFunction(Modified[T]):
    def __init__(self, fn: Callable[P, T], modifiers: ModifierManager, default=None) -> None:
        self.default = default
        self.modifiers = modifiers
        self.async_def = asyncio.iscoroutinefunction(fn)
        self.decorated_fn = self.__decorate(fn)
    
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Union[Awaitable[T], T]:
        return self.decorated_fn(*args, **kwargs)
    
    def __decorate(self, func):
        _helpers._validate_wrapped_fn(func)
        if asyncio.iscoroutinefunction(func):
            return self.__decorate_async(func)
        elif callable(func):
            return self.__decorate_sync(func)
        raise NotImplementedError(f'Unable to decorate {func}')
    
    @property
    def _sync_default(self) -> bool:
        """If user did not specify a default, we defer to the function. 'def' vs 'async def'"""
        return True if self.default == 'sync' else False if self.default == 'async' else not self.async_def
    
    def __run_sync(self, kwargs: dict):
        try:
            # If a flag was specified in the kwargs, we will defer to it.
            return _kwargs.is_sync(kwargs, pop_flag=True)
        except exceptions.NoFlagsFound:
            # No flag specified in the kwargs, we will defer to 'default'.
            return self._sync_default
    
    def __decorate_async(self, func):
        modified_async_function = self.modifiers.apply_async_modifiers(func)
        _await = self.modifiers.apply_sync_modifiers(_helpers._await)
        @functools.wraps(func)
        def async_wrap(*args: P.args, **kwargs: P.kwargs) -> Union[Awaitable[T], T]:  # type: ignore [name-defined]
            should_await = self.__run_sync(kwargs) # Must take place before coro is created, we're popping a kwarg.
            coro = modified_async_function(*args, **kwargs)
            return _await(coro) if should_await else coro
        return async_wrap
    
    def __decorate_sync(self, func):
        modified_sync_function = self.modifiers.apply_sync_modifiers(func)
        @functools.wraps(func)
        @self.modifiers.apply_async_modifiers
        async def create_awaitable(*args: P.args, **kwargs: P.kwargs) -> T:
            return await asyncio.get_event_loop().run_in_executor(self.modifiers.executor, modified_sync_function, *args, **kwargs)
        @functools.wraps(func)
        def sync_wrap(*args: P.args, **kwargs: P.kwargs) -> Union[Awaitable[T], T]:  # type: ignore [name-defined]
            if self.__run_sync(kwargs):
                return modified_sync_function(*args, **kwargs)
            return create_awaitable(*args, **kwargs)
        return sync_wrap
