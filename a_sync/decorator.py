
from typing import Awaitable, Callable, Literal, Optional, Union, overload

from typing_extensions import Unpack  # type: ignore [attr-defined]

from a_sync import _flags, config
from a_sync._typing import ModifierKwargs, P, T
from a_sync.modified import ASyncDecorator
from a_sync.modifiers import ModifierManager

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
    **modifiers: Unpack[ModifierKwargs],
) -> Callable[P, Awaitable[T]]:...  # type: ignore [misc]

@overload # sync def none default
def a_sync(  # type: ignore [misc]
    coro_fn: Callable[P, T] = None,  # type: ignore [misc]
    default: Literal[None] = None,
    **modifiers: Unpack[ModifierKwargs],
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
    **modifiers: Unpack[ModifierKwargs],
) -> Callable[[Union[Callable[P, Awaitable[T]], Callable[P, T]]], Callable[P, Awaitable[T]]]:...  # type: ignore [misc]

@overload # if you try to use default as the only arg
def a_sync(
    coro_fn: Literal['async'] = None,
    default: Literal[None] = None,
    **modifiers: Unpack[ModifierKwargs],
) -> Callable[[Union[Callable[P, Awaitable[T]], Callable[P, T]]], Callable[P, Awaitable[T]]]:...  # type: ignore [misc]

# a_sync(some_fn, default='async')

@overload # async def, async default
def a_sync(
    coro_fn: Callable[P, Awaitable[T]] = None,  # type: ignore [misc]
    default: Literal['async'] = None,
    **modifiers: Unpack[ModifierKwargs],
) -> Callable[P, Awaitable[T]]:...  # type: ignore [misc]

@overload # sync def async default
def a_sync(  # type: ignore [misc]
    coro_fn: Callable[P, T] = None,  # type: ignore [misc]
    default: Literal['async'] = None,
    **modifiers: Unpack[ModifierKwargs],
) -> Callable[P, Awaitable[T]]:...  # type: ignore [misc]

# a_sync(some_fn, default='sync')

@overload # async def, async default
def a_sync(
    coro_fn: Callable[P, Awaitable[T]] = None,  # type: ignore [misc]
    default: Literal['sync'] = None,
    **modifiers: Unpack[ModifierKwargs],
) -> Callable[P, T]:...  # type: ignore [misc]

@overload # sync def async default
def a_sync(  # type: ignore [misc]
    coro_fn: Callable[P, T] = None,  # type: ignore [misc]
    default: Literal['sync'] = None,
    **modifiers: Unpack[ModifierKwargs],
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
    **modifiers: Unpack[ModifierKwargs],
) -> Callable[[Union[Callable[P, Awaitable[T]], Callable[P, T]]], Callable[P, T]]:...  # type: ignore [misc]

@overload # if you try to use default as the only arg
def a_sync(
    coro_fn: Literal['sync'] = None,
    default: Literal[None] = None,
    **modifiers: Unpack[ModifierKwargs],
) -> Callable[[Union[Callable[P, Awaitable[T]], Callable[P, T]]], Callable[P, T]]:...  # type: ignore [misc]

'''
lib defaults:
async settings
    cache_type: Optional[Literal['memory']] = None,
    cache_typed: bool = False,
    ram_cache_maxsize: Optional[int] = -1,
    ram_cache_ttl: Optional[int] = None,
    runs_per_minute: Optional[int] = None,
    semaphore: semaphores.SemaphoreSpec = semaphores.dummy_semaphore,
sync settings
    executor: Executor = config.default_sync_executor
'''
    
# catchall
def a_sync(
    coro_fn: Optional[Union[Callable[P, Awaitable[T]], Callable[P, T]]] = None,  # type: ignore [misc]
    default: Literal['sync', 'async', None] = config.DEFAULT_MODE,
    **modifiers: Unpack[ModifierKwargs],  # default values are set by passing these kwargs into a ModifierManager object.
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
    modifiers: ModifierManager = ModifierManager(modifiers)
    
    # If the dev tried passing a default as an arg instead of a kwarg, ie: @a_sync('sync')...
    if coro_fn in ['async', 'sync']:
        default = coro_fn
        coro_fn = None
        
    if default not in ['async', 'sync', None]:
        raise 
    
    # Decorator
    
    a_sync_deco = ASyncDecorator(modifiers, default)
    return a_sync_deco if coro_fn is None else a_sync_deco(coro_fn)
