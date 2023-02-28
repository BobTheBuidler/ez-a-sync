
import asyncio
import functools
from concurrent.futures._base import Executor
from typing import (Awaitable, Callable, Literal, Optional, TypeVar, Union,
                    overload)

from typing_extensions import ParamSpec  # type: ignore [attr-defined]

from a_sync import (_flags, _helpers, _kwargs, config, exceptions,
                    rate_limiting, semaphores)

P = ParamSpec("P")
T = TypeVar("T")

########################
# The a_sync decorator #
########################

# @a_sync
# def some_fn():
#     pass
#
# @a_sync
# async def some_fn():
#     pass

@overload # async def, None default
def a_sync(
    coro_fn: Callable[P, Awaitable[T]] = None,  # type: ignore [misc]
    default: Literal[None] = None,
    # async settings
    runs_per_minute: Optional[int] = None,
    semaphore: semaphores.SemaphoreSpec = semaphores.dummy_semaphore,
    # sync settings
    executor: Executor = config.default_sync_executor,
) -> Callable[P, Awaitable[T]]:...  # type: ignore [misc]

@overload # sync def none default
def a_sync(  # type: ignore [misc]
    coro_fn: Callable[P, T] = None,  # type: ignore [misc]
    default: Literal[None] = None,
    # async settings
    runs_per_minute: Optional[int] = None,
    semaphore: semaphores.SemaphoreSpec = semaphores.dummy_semaphore,
    # sync settings
    executor: Executor = config.default_sync_executor,
) -> Callable[P, T]:...  # type: ignore [misc]

# @a_sync(default='async')
# def some_fn():
#     pass
#
# @a_sync(default='async')
# async def some_fn():
#     pass
#
# NOTE These should output a decorator that will be applied to 'some_fn'

@overload 
def a_sync(
    coro_fn: Literal[None] = None,
    default: Literal['async'] = None,
    # async settings
    runs_per_minute: Optional[int] = None,
    semaphore: semaphores.SemaphoreSpec = semaphores.dummy_semaphore,
    # sync settings
    executor: Executor = config.default_sync_executor,
) -> Callable[[Union[Callable[P, Awaitable[T]], Callable[P, T]]], Callable[P, Awaitable[T]]]:...  # type: ignore [misc]

@overload # if you try to use default as the only arg
def a_sync(
    coro_fn: Literal['async'] = None,
    default: Literal[None] = None,
    # async settings
    runs_per_minute: Optional[int] = None,
    semaphore: semaphores.SemaphoreSpec = semaphores.dummy_semaphore,
    # sync settings
    executor: Executor = config.default_sync_executor,
) -> Callable[[Union[Callable[P, Awaitable[T]], Callable[P, T]]], Callable[P, Awaitable[T]]]:...  # type: ignore [misc]

# a_sync(some_fn, default='async')

@overload # async def, async default
def a_sync(
    coro_fn: Callable[P, Awaitable[T]] = None,  # type: ignore [misc]
    default: Literal['async'] = None,
    # async settings
    runs_per_minute: Optional[int] = None,
    semaphore: semaphores.SemaphoreSpec = semaphores.dummy_semaphore,
    # sync settings
    executor: Executor = config.default_sync_executor,
) -> Callable[P, Awaitable[T]]:...  # type: ignore [misc]

@overload # sync def async default
def a_sync(  # type: ignore [misc]
    coro_fn: Callable[P, T] = None,  # type: ignore [misc]
    default: Literal['async'] = None,
    # async settings
    runs_per_minute: Optional[int] = None,
    semaphore: semaphores.SemaphoreSpec = semaphores.dummy_semaphore,
    # sync settings
    executor: Executor = config.default_sync_executor,
) -> Callable[P, Awaitable[T]]:...  # type: ignore [misc]

# a_sync(some_fn, default='sync')

@overload # async def, async default
def a_sync(
    coro_fn: Callable[P, Awaitable[T]] = None,  # type: ignore [misc]
    default: Literal['sync'] = None,
    # async settings
    runs_per_minute: Optional[int] = None,
    semaphore: semaphores.SemaphoreSpec = semaphores.dummy_semaphore,
    # sync settings
    executor: Executor = config.default_sync_executor,
) -> Callable[P, T]:...  # type: ignore [misc]

@overload # sync def async default
def a_sync(  # type: ignore [misc]
    coro_fn: Callable[P, T] = None,  # type: ignore [misc]
    default: Literal['sync'] = None,
    # async settings
    runs_per_minute: Optional[int] = None,
    semaphore: semaphores.SemaphoreSpec = semaphores.dummy_semaphore,
    # sync settings
    executor: Executor = config.default_sync_executor,
) -> Callable[P, T]:...  # type: ignore [misc]

# @a_sync(default='sync')
# def some_fn():
#     pass
#
# @a_sync(default='sync')
# async def some_fn():
#     pass
#
# NOTE These should output a decorator that will be applied to 'some_fn'

@overload 
def a_sync(  # type: ignore [misc]
    coro_fn: Literal[None] = None,
    default: Literal['sync'] = None,
    # async settings
    runs_per_minute: Optional[int] = None,
    semaphore: semaphores.SemaphoreSpec = semaphores.dummy_semaphore,
    # sync settings
    executor: Executor = config.default_sync_executor,
) -> Callable[[Union[Callable[P, Awaitable[T]], Callable[P, T]]], Callable[P, T]]:...  # type: ignore [misc]

@overload # if you try to use default as the only arg
def a_sync(
    coro_fn: Literal['sync'] = None,
    default: Literal[None] = None,
    # async settings
    runs_per_minute: Optional[int] = None,
    semaphore: semaphores.SemaphoreSpec = semaphores.dummy_semaphore,
    # sync settings
    executor: Executor = config.default_sync_executor,
) -> Callable[[Union[Callable[P, Awaitable[T]], Callable[P, T]]], Callable[P, T]]:...  # type: ignore [misc]

# catchall
def a_sync(
    coro_fn: Optional[Union[Callable[P, Awaitable[T]], Callable[P, T]]] = None,  # type: ignore [misc]
    default: Literal['sync', 'async', None] = None,
    # async settings
    runs_per_minute: Optional[int] = None,
    semaphore: semaphores.SemaphoreSpec = semaphores.dummy_semaphore,
    # sync settings
    executor: Executor = config.default_sync_executor,
) -> Union[  # type: ignore [misc]
    # sync coro_fn, default=None
    Callable[P, T],
    # async coro_fn, default=None
    Callable[P, Awaitable[T]],
    # coro_fn=None, default='async'
    Callable[[Union[Callable[P, Awaitable[T]], Callable[P, T]]], Callable[P, Awaitable[T]]],
    # coro_fn=None, default='sync'
    Callable[[Union[Callable[P, Awaitable[T]], Callable[P, T]]], Callable[P, T]],
]:
    f"""
    A coroutine function decorated with this decorator can be called as a sync function by passing a boolean value for any of these kwargs: {_flags.VIABLE_FLAGS}

    ######################
    # async def examples #
    ######################

    @a_sync
    async def some_fn():
        reurn True
    
    await some_fn() == True
    some_fn(sync=True) == True

    
    @a_sync(default=None)
    async def some_fn():
        reurn True
    
    await some_fn() == True
    some_fn(sync=True) == True

    
    @a_sync(default='async')
    async def some_fn():
        reurn True
    
    await some_fn() == True
    some_fn(sync=True) == True
    

    @a_sync(default='sync')
    async def some_fn():
        reurn True
    
    some_fn() == True
    await some_fn(sync=False) == True

    
    # TODO: in a future release, I will make this usable with sync functions as well

    ################
    # def examples #
    ################

    @a_sync
    def some_fn():
        reurn True
    
    some_fn() == True
    await some_fn(sync=False) == True
    

    @a_sync(default=None)
    def some_fn():
        reurn True
    
    some_fn() == True
    await some_fn(sync=False) == True


    @a_sync(default='async')
    def some_fn():
        reurn True
    
    await some_fn() == True
    some_fn(sync=True) == True


    @a_sync(default='sync')
    def some_fn():
        reurn True
    
    some_fn() == True
    await some_fn(sync=False) == True
    """
    
    # If the dev tried passing a default as an arg instead of a kwarg, ie: @a_sync('sync')...
    if coro_fn in ['async', 'sync']:
        default = coro_fn
        coro_fn = None
        
    if default not in ['async', 'sync', None]:
        raise ValueError(f"'default' must be either 'sync', 'async', or None. You passed {default}.")
    
    # Modifiers - Additional functionality will be added by stacking decorators here.
    
    def apply_async_modifiers(coro_fn: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(coro_fn)
        @semaphores.apply_semaphore(semaphore)
        @rate_limiting.apply_rate_limit(runs_per_minute)
        async def async_modifier_wrap(*args: P.args, **kwargs: P.kwargs) -> T:
            return await coro_fn(*args, **kwargs)
        return async_modifier_wrap
    
    def apply_sync_modifiers(function: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(function)
        # NOTE There are no sync modifiers at this time but they will be added here for my convenience.
        def sync_modifier_wrap(*args: P.args, **kwargs: P.kwargs) -> T:
            return function(*args, **kwargs)
        return sync_modifier_wrap
    
    
    # Decorator
    
    def a_sync_deco(function: Callable[P, Awaitable[T]]) -> Union[Callable[P, Awaitable[T]], Callable[P, T]]:  # type: ignore [misc]
        
        # First, are we using this decorator correctly?
        _helpers._validate_wrapped_fn(function)
        
        # What kind of function are we decorating?
        if asyncio.iscoroutinefunction(function):
            # NOTE: The following code applies to async functions defined with 'async def'
            
            @functools.wraps(function)
            def async_wrap(*args: P.args, **kwargs: P.kwargs) -> Union[Awaitable[T], T]:  # type: ignore [name-defined]
                should_await = _run_sync(kwargs, default or 'async') # Must take place before coro is created.
                modified_function = apply_async_modifiers(function)
                coro = modified_function(*args, **kwargs)
                return apply_sync_modifiers(_helpers._sync)(coro) if should_await else coro
            return async_wrap
        
        elif callable(function):
            # NOTE: The following code applies to sync functions defined with 'def'
            modified_sync_function = apply_sync_modifiers(function)
            
            @apply_async_modifiers
            @functools.wraps(function)
            async def create_awaitable(*args: P.args, **kwargs: P.kwargs) -> T:
                return await apply_async_modifiers(asyncio.get_event_loop().run_in_executor)(
                    executor, modified_sync_function, *args, **kwargs
                )
                
            @functools.wraps(function)
            def sync_wrap(*args: P.args, **kwargs: P.kwargs) -> Union[Awaitable[T], T]:  # type: ignore [name-defined]
                if _run_sync(kwargs, default = default or 'sync'):
                    return modified_sync_function(*args, **kwargs)
                return create_awaitable(*args, **kwargs)
            
            return sync_wrap
        
        raise RuntimeError(f"a_sync's first arg must be callable. You passed {function}.")
    
    return a_sync_deco if coro_fn is None else a_sync_deco(coro_fn)


def _run_sync(kwargs: dict, default: Literal['sync', 'async']):
    # If a flag was specified in the kwargs, we will defer to it.
    try:
        return _kwargs.is_sync(kwargs, pop_flag=True)
    except exceptions.NoFlagsFound:
        # No flag specified in the kwargs, we will defer to 'default'.
        if default == 'sync':
            return True
        elif default == 'async':
            return False
        else:
            raise NotImplementedError(default)
