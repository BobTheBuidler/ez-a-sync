# mypy: disable-error-code=valid-type
# mypy: disable-error-code=misc
from a_sync import _flags, config
from a_sync._typing import *
from a_sync.modified import ASyncDecorator, ASyncFunction

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

@overload
def a_sync(
    **modifiers: Unpack[ModifierKwargs],
) -> AnyFn[P, T]:...

@overload # async def, None default
def a_sync(  
    coro_fn: CoroFn[P, T],
    default: Literal[None] = None,
    **modifiers: Unpack[ModifierKwargs],
) -> CoroFn[P, T]:...

@overload # sync def none default
def a_sync(  
    coro_fn: SyncFn[P, T],
    default: Literal[None] = None,
    **modifiers: Unpack[ModifierKwargs],
) -> SyncFn[P, T]:...

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
    coro_fn: Literal[None],
    default: Literal['async'],
    **modifiers: Unpack[ModifierKwargs],
) -> AllToAsyncDecorator[P, T]:...

@overload # if you try to use default as the only arg
def a_sync(  
    coro_fn: Literal['async'],
    default: Literal[None],
    **modifiers: Unpack[ModifierKwargs],
) -> AllToAsyncDecorator[P, T]:...

# a_sync(some_fn, default='async')

@overload # async def, async default
def a_sync(  
    coro_fn: CoroFn[P, T],
    default: Literal['async'],
    **modifiers: Unpack[ModifierKwargs],
) -> CoroFn[P, T]:...

@overload # sync def async default
def a_sync(  
    coro_fn: SyncFn[P, T],
    default: Literal['async'],
    **modifiers: Unpack[ModifierKwargs],
) -> CoroFn[P, T]:...

# a_sync(some_fn, default='sync')

@overload # async def, sync default
def a_sync(  
    coro_fn: CoroFn[P, T],
    default: Literal['sync'],
    **modifiers: Unpack[ModifierKwargs],
) -> SyncFn[P, T]:...

@overload # sync def sync default
def a_sync(  
    coro_fn: SyncFn[P, T],
    default: Literal['sync'],
    **modifiers: Unpack[ModifierKwargs],
) -> SyncFn[P, T]:...

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
def a_sync(  
    coro_fn: Literal[None],
    default: Literal['sync'],
    **modifiers: Unpack[ModifierKwargs],
) -> AllToSyncDecorator[P, T]:...

@overload # if you try to use default as the only arg
def a_sync(  
    coro_fn: Literal['sync'],
    default: Literal[None] = None,
    **modifiers: Unpack[ModifierKwargs],
) -> AllToSyncDecorator[P, T]:...

@overload # if you try to use default as the only arg
def a_sync(  
    coro_fn: Literal['sync'],
    default: Literal[None],
    **modifiers: Unpack[ModifierKwargs],
) -> AllToSyncDecorator[P, T]:...
    
# catchall
def a_sync(  
    coro_fn: Optional[AnyFn[P, T]] = None,
    default: DefaultMode = config.DEFAULT_MODE,
    **modifiers: Unpack[ModifierKwargs],  # default values are set by passing these kwargs into a ModifierManager object.
) -> Union[ASyncDecorator[P, T], ASyncFunction[P, T]]:
    f"""
    A coroutine function decorated with this decorator can be called as a sync function by passing a boolean value for any of these kwargs: {_flags.VIABLE_FLAGS}
    
    lib defaults:
    async settings
        cache_type: CacheType = None,            - This can be None or 'memory'. 'memory' is a lru cache which can be modified with the 'cache_typed','ram_cache_maxsize','ram_cache_ttl' modifiers.
        cache_typed: bool = False,               - Set to True if you want types considered treated for cache keys. ie with cache_typed=True, Decimal(0) and 0 will be considered separate keys.
        ram_cache_maxsize: Optional[int] = -1,   - The maxsize for your lru cache. None if cache is unbounded. If you set this value without specifying a cache type, 'memory' will automatically be applied.
        ram_cache_ttl: Optional[int] = None,     - The ttl for items in your lru cache. Set to None. If you set this value without specifying a cache type, 'memory' will automatically be applied.
        runs_per_minute: Optional[int] = None,   - Setting this value enables a rate limiter for the decorated function.
        semaphore: SemaphoreSpec = None,         - drop in a Semaphore for your async defined functions.
    sync settings
        executor: Executor = config.default_sync_executor

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
        default = coro_fn  # type: ignore [assignment]
        coro_fn = None
    
    deco = ASyncDecorator(default=default, **modifiers)
    return deco if coro_fn is None else deco(coro_fn)  # type: ignore [arg-type]
