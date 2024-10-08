# mypy: disable-error-code=valid-type
# mypy: disable-error-code=misc
from a_sync._typing import *
from a_sync.a_sync import _flags, config
from a_sync.a_sync.function import (ASyncDecorator, ASyncFunction, ASyncDecoratorAsyncDefault, 
                             ASyncDecoratorSyncDefault, ASyncFunctionAsyncDefault, 
                             ASyncFunctionSyncDefault)

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
    default: Literal["async"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncDecoratorAsyncDefault:...

@overload
def a_sync(
    default: Literal["sync"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncDecoratorSyncDefault:...

@overload
def a_sync(
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncDecorator:...

@overload # async def, None default
def a_sync(  
    coro_fn: CoroFn[P, T],
    default: Literal[None] = None,
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncFunctionAsyncDefault[P, T]:...

@overload # sync def none default
def a_sync(  
    coro_fn: SyncFn[P, T],
    default: Literal[None] = None,
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncFunctionSyncDefault[P, T]:...

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
) -> ASyncDecoratorAsyncDefault:...

@overload # if you try to use default as the only arg
def a_sync(  
    coro_fn: Literal['async'],
    default: Literal[None],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncDecoratorAsyncDefault:...

# a_sync(some_fn, default='async')

@overload # async def, async default
def a_sync(  
    coro_fn: CoroFn[P, T],
    default: Literal['async'],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncFunctionAsyncDefault[P, T]:...

@overload # sync def async default
def a_sync(  
    coro_fn: SyncFn[P, T],
    default: Literal['async'],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncFunctionAsyncDefault[P, T]:...

# a_sync(some_fn, default='sync')

@overload # async def, sync default
def a_sync(  
    coro_fn: CoroFn[P, T],
    default: Literal['sync'],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncFunctionSyncDefault:...

@overload # sync def sync default
def a_sync(  
    coro_fn: SyncFn[P, T],
    default: Literal['sync'],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncFunctionSyncDefault:...

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
) -> ASyncDecoratorSyncDefault:...

@overload # if you try to use default as the only arg
def a_sync(  
    coro_fn: Literal['sync'],
    default: Literal[None] = None,
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncDecoratorSyncDefault:...

@overload # if you try to use default as the only arg
def a_sync(  
    coro_fn: Literal['sync'],
    default: Literal[None],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncDecoratorSyncDefault:...
    
# catchall
def a_sync(  
    coro_fn: Optional[AnyFn[P, T]] = None,
    default: DefaultMode = config.DEFAULT_MODE,
    **modifiers: Unpack[ModifierKwargs],  # default values are set by passing these kwargs into a ModifierManager object.
) -> Union[ASyncDecorator, ASyncFunction[P, T]]:
    """
    A versatile decorator that enables both synchronous and asynchronous execution of functions.

    This decorator allows a function to be called either synchronously or asynchronously,
    depending on the context and parameters. It provides a powerful way to write code
    that can be used in both synchronous and asynchronous environments.

    Args:
        coro_fn: The function to be decorated. Can be either a coroutine function or a regular function.
        default: Determines the default execution mode. Can be 'async', 'sync', or None.
                 If None, the mode is inferred from the decorated function type.
        **modifiers: Additional keyword arguments to modify the behavior of the decorated function.
                     See :class:`ModifierKwargs` for available options.
    
    Modifiers:
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

    Returns:
        An :class:`~ASyncDecorator` if used as a decorator factory, or an :class:`~ASyncFunction`
        if used directly on a function.

    Examples:
        The decorator can be used in several ways.

        1. As a simple decorator:
        ```python
        >>> @a_sync
        ... async def some_async_fn():
        ...     return True
        >>> await some_fn()
        True
        >>> some_fn(sync=True)
        True
        ```
        ```
        >>> @a_sync
        ... def some_sync_fn():
        ...     return True
        >>> some_sync_fn()
        True
        >>> some_sync_fn(sync=False)
        <coroutine object some_sync_fn at 0x12345678>
        ```

        2. As a decorator with default mode specified:
        ```python
        >>> @a_sync(default='sync')
        ... async def some_fn():
        ...     return True
        ...
        >>> some_fn()
        True
        ```

        3. As a decorator with modifiers:
        ```python
        >>> @a_sync(cache_type='memory', runs_per_minute=60)
        ... async def some_fn():
        ...    return True
        ...
        >>> some_fn(sync=True)
        True
        ```

        4. Applied directly to a function:
        ```python
        >>> some_fn = a_sync(some_existing_function, default='sync')
        >>> some_fn()
        "some return value"
        ```

    The decorated function can then be called either synchronously or asynchronously:

    ```python
    result = some_fn()  # Synchronous call
    result = await some_fn()  # Asynchronous call
    ```

    The execution mode can also be explicitly specified during the call:

    ```python
    result = some_fn(sync=True)  # Force synchronous execution
    result = await some_fn(sync=False)  # Force asynchronous execution
    ```

    This decorator is particularly useful for libraries that need to support
    both synchronous and asynchronous usage, or for gradually migrating
    synchronous code to asynchronous without breaking existing interfaces.
    """
    
    # If the dev tried passing a default as an arg instead of a kwarg, ie: @a_sync('sync')...
    if coro_fn in ['async', 'sync']:
        default = coro_fn  # type: ignore [assignment]
        coro_fn = None
    
    if default == "sync":
        deco = ASyncDecoratorSyncDefault(default=default, **modifiers)
    elif default == "async":
        deco = ASyncDecoratorAsyncDefault(default=default, **modifiers)
    else:
        deco = ASyncDecorator(default=default, **modifiers)
    return deco if coro_fn is None else deco(coro_fn)  # type: ignore [arg-type]

# TODO: in a future release, I will make this usable with sync functions as well