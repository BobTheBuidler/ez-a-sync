# mypy: disable-error-code=valid-type
# mypy: disable-error-code=misc
from a_sync._typing import *
from a_sync.a_sync import _flags, config
from a_sync.a_sync.function import (
    ASyncDecorator,
    ASyncFunction,
    ASyncDecoratorAsyncDefault,
    ASyncDecoratorSyncDefault,
    ASyncFunctionAsyncDefault,
    ASyncFunctionSyncDefault,
)

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
) -> ASyncDecoratorAsyncDefault:
    """
    Creates an asynchronous default decorator.

    Args:
        default: Specifies the default execution mode as 'async'.
        **modifiers: Additional keyword arguments to modify the behavior of the decorated function.

    Examples:
        Basic usage with an asynchronous default:

        >>> @a_sync(default='async')
        ... async def my_function():
        ...     return True
        >>> await my_function()
        True
        >>> my_function(sync=True)
        True

    See Also:
        :class:`ASyncDecoratorAsyncDefault`
    """


@overload
def a_sync(
    default: Literal["sync"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncDecoratorSyncDefault:
    """
    Creates a synchronous default decorator.

    Args:
        default: Specifies the default execution mode as 'sync'.
        **modifiers: Additional keyword arguments to modify the behavior of the decorated function.

    Examples:
        Basic usage with a synchronous default:

        >>> @a_sync(default='sync')
        ... def my_function():
        ...     return True
        >>> my_function()
        True
        >>> await my_function(sync=False)
        True

    See Also:
        :class:`ASyncDecoratorSyncDefault`
    """


@overload
def a_sync(
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncDecorator:
    """
    Creates a decorator with no default execution mode specified.

    Args:
        **modifiers: Additional keyword arguments to modify the behavior of the decorated function.

    Examples:
        Usage without specifying a default mode:

        >>> @a_sync
        ... async def my_function():
        ...     return True
        >>> await my_function()
        True
        >>> my_function(sync=True)
        True

    See Also:
        :class:`ASyncDecorator`
    """


@overload  # async def, None default
def a_sync(
    coro_fn: CoroFn[P, T],
    default: Literal[None] = None,
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncFunctionAsyncDefault[P, T]:
    """
    Decorates an asynchronous function with no default execution mode specified.

    Args:
        coro_fn: The coroutine function to be decorated.
        default: Specifies no default execution mode.
        **modifiers: Additional keyword arguments to modify the behavior of the decorated function.

    Examples:
        Decorating an asynchronous function without a default mode:

        >>> async def my_function():
        ...     return True
        >>> decorated_function = a_sync(my_function)
        >>> await decorated_function()
        True
        >>> decorated_function(sync=True)
        True

    See Also:
        :class:`ASyncFunctionAsyncDefault`
    """


@overload  # sync def none default
def a_sync(
    coro_fn: SyncFn[P, T],
    default: Literal[None] = None,
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncFunctionSyncDefault[P, T]:
    """
    Decorates a synchronous function with no default execution mode specified.

    Args:
        coro_fn: The synchronous function to be decorated.
        default: Specifies no default execution mode.
        **modifiers: Additional keyword arguments to modify the behavior of the decorated function.

    Examples:
        Decorating a synchronous function without a default mode:

        >>> def my_function():
        ...     return True
        >>> decorated_function = a_sync(my_function)
        >>> decorated_function()
        True
        >>> await decorated_function(sync=False)
        True

    See Also:
        :class:`ASyncFunctionSyncDefault`
    """


@overload
def a_sync(
    coro_fn: Literal[None],
    default: Literal["async"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncDecoratorAsyncDefault:
    """
    Creates an asynchronous default decorator with no function specified.

    Args:
        coro_fn: Specifies no function.
        default: Specifies the default execution mode as 'async'.
        **modifiers: Additional keyword arguments to modify the behavior of the decorated function.

    Examples:
        Creating an asynchronous default decorator without a function:

        >>> @a_sync(default='async')
        ... async def my_function():
        ...     return True
        >>> await my_function()
        True
        >>> my_function(sync=True)
        True

    See Also:
        :class:`ASyncDecoratorAsyncDefault`
    """


@overload  # if you try to use default as the only arg
def a_sync(
    coro_fn: Literal["async"],
    default: Literal[None],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncDecoratorAsyncDefault:
    """
    Creates an asynchronous default decorator with no default execution mode specified.

    Args:
        coro_fn: Specifies the default execution mode as 'async'.
        default: Specifies no default execution mode.
        **modifiers: Additional keyword arguments to modify the behavior of the decorated function.

    Examples:
        Using 'async' as the only argument:

        >>> @a_sync('async')
        ... async def my_function():
        ...     return True
        >>> await my_function()
        True
        >>> my_function(sync=True)
        True

    See Also:
        :class:`ASyncDecoratorAsyncDefault`
    """


@overload  # async def, async default
def a_sync(
    coro_fn: CoroFn[P, T],
    default: Literal["async"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncFunctionAsyncDefault[P, T]:
    """
    Decorates an asynchronous function with an asynchronous default execution mode.

    Args:
        coro_fn: The coroutine function to be decorated.
        default: Specifies the default execution mode as 'async'.
        **modifiers: Additional keyword arguments to modify the behavior of the decorated function.

    Examples:
        Decorating an asynchronous function with an async default:

        >>> async def my_function():
        ...     return True
        >>> decorated_function = a_sync(my_function, default='async')
        >>> await decorated_function()
        True
        >>> decorated_function(sync=True)
        True

    See Also:
        :class:`ASyncFunctionAsyncDefault`
    """


@overload  # sync def async default
def a_sync(
    coro_fn: SyncFn[P, T],
    default: Literal["async"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncFunctionAsyncDefault[P, T]:
    """
    Decorates a synchronous function with an asynchronous default execution mode.

    Args:
        coro_fn: The synchronous function to be decorated.
        default: Specifies the default execution mode as 'async'.
        **modifiers: Additional keyword arguments to modify the behavior of the decorated function.

    Examples:
        Decorating a synchronous function with an async default:

        >>> def my_function():
        ...     return True
        >>> decorated_function = a_sync(my_function, default='async')
        >>> await decorated_function()
        True
        >>> decorated_function(sync=True)
        True

    See Also:
        :class:`ASyncFunctionAsyncDefault`
    """


@overload  # async def, sync default
def a_sync(
    coro_fn: CoroFn[P, T],
    default: Literal["sync"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncFunctionSyncDefault:
    """
    Decorates an asynchronous function with a synchronous default execution mode.

    Args:
        coro_fn: The coroutine function to be decorated.
        default: Specifies the default execution mode as 'sync'.
        **modifiers: Additional keyword arguments to modify the behavior of the decorated function.

    Examples:
        Decorating an asynchronous function with a sync default:

        >>> async def my_function():
        ...     return True
        >>> decorated_function = a_sync(my_function, default='sync')
        >>> decorated_function()
        True
        >>> await decorated_function(sync=False)
        True

    See Also:
        :class:`ASyncFunctionSyncDefault`
    """


@overload  # sync def sync default
def a_sync(
    coro_fn: SyncFn[P, T],
    default: Literal["sync"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncFunctionSyncDefault:
    """
    Decorates a synchronous function with a synchronous default execution mode.

    Args:
        coro_fn: The synchronous function to be decorated.
        default: Specifies the default execution mode as 'sync'.
        **modifiers: Additional keyword arguments to modify the behavior of the decorated function.

    Examples:
        Decorating a synchronous function with a sync default:

        >>> def my_function():
        ...     return True
        >>> decorated_function = a_sync(my_function, default='sync')
        >>> decorated_function()
        True
        >>> await decorated_function(sync=False)
        True

    See Also:
        :class:`ASyncFunctionSyncDefault`
    """


@overload
def a_sync(
    coro_fn: Literal[None],
    default: Literal["sync"],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncDecoratorSyncDefault:
    """
    Creates a synchronous default decorator with no function specified.

    Args:
        coro_fn: Specifies no function.
        default: Specifies the default execution mode as 'sync'.
        **modifiers: Additional keyword arguments to modify the behavior of the decorated function.

    Examples:
        Creating a synchronous default decorator without a function:

        >>> @a_sync(default='sync')
        ... def my_function():
        ...     return True
        >>> my_function()
        True
        >>> await my_function(sync=False)
        True

    See Also:
        :class:`ASyncDecoratorSyncDefault`
    """


@overload  # if you try to use default as the only arg
def a_sync(
    coro_fn: Literal["sync"],
    default: Literal[None] = None,
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncDecoratorSyncDefault:
    """
    Creates a synchronous default decorator with no default execution mode specified.

    Args:
        coro_fn: Specifies the default execution mode as 'sync'.
        default: Specifies no default execution mode.
        **modifiers: Additional keyword arguments to modify the behavior of the decorated function.

    Examples:
        Using 'sync' as the only argument:

        >>> @a_sync('sync')
        ... def my_function():
        ...     return True
        >>> my_function()
        True
        >>> await my_function(sync=False)
        True

    See Also:
        :class:`ASyncDecoratorSyncDefault`
    """


@overload  # if you try to use default as the only arg
def a_sync(
    coro_fn: Literal["sync"],
    default: Literal[None],
    **modifiers: Unpack[ModifierKwargs],
) -> ASyncDecoratorSyncDefault:
    """
    Creates a synchronous default decorator with no default execution mode specified.

    Args:
        coro_fn: Specifies the default execution mode as 'sync'.
        default: Specifies no default execution mode.
        **modifiers: Additional keyword arguments to modify the behavior of the decorated function.

    Examples:
        Using 'sync' as the only argument:

        >>> @a_sync('sync')
        ... def my_function():
        ...     return True
        >>> my_function()
        True
        >>> await my_function(sync=False)
        True

    See Also:
        :class:`ASyncDecoratorSyncDefault`
    """


# catchall
def a_sync(
    coro_fn: Optional[AnyFn[P, T]] = None,
    default: DefaultMode = config.DEFAULT_MODE,
    **modifiers: Unpack[
        ModifierKwargs
    ],  # default values are set by passing these kwargs into a ModifierManager object.
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
        The following modifiers can be used to customize the behavior of the decorator:

        - cache_type: Can be None or 'memory'. 'memory' is an LRU cache which can be modified with
          the 'cache_typed', 'ram_cache_maxsize', and 'ram_cache_ttl' modifiers.
        - cache_typed: Set to True if you want types considered for cache keys. For example, with
          cache_typed=True, Decimal(0) and 0 will be considered separate keys.
        - ram_cache_maxsize: The max size for your LRU cache. None if the cache is unbounded. If you
          set this value without specifying a cache type, 'memory' will automatically be applied.
        - ram_cache_ttl: The TTL for items in your LRU cache. Set to None. If you set this value
          without specifying a cache type, 'memory' will automatically be applied.
        - runs_per_minute: Setting this value enables a rate limiter for the decorated function.
        - semaphore: Drop in a Semaphore for your async defined functions.
        - executor: The executor for the synchronous function. Set to the library's default of
          config.default_sync_executor.

    Examples:
        The decorator can be used in several ways.

        1. As a simple decorator:
            >>> @a_sync
            ... async def some_async_fn():
            ...     return True
            >>> await some_async_fn()
            True
            >>> some_async_fn(sync=True)
            True

            >>> @a_sync
            ... def some_sync_fn():
            ...     return True
            >>> some_sync_fn()
            True
            >>> some_sync_fn(sync=False)
            <coroutine object some_sync_fn at 0x7fb4f5fb49c0>

        2. As a decorator with default mode specified:
            >>> @a_sync(default='sync')
            ... async def some_fn():
            ...     return True
            ...
            >>> some_fn()
            True
            >>> some_fn(sync=False)
            <coroutine object some_fn at 0x7fb4f5fb49c0>

            >>> @a_sync('async')
            ... def some_fn():
            ...     return True
            ...
            >>> some_fn()
            <coroutine object some_fn at 0x7fb4f5fb49c0>
            >>> some_fn(asynchronous=False)
            True

        3. As a decorator with modifiers:
            >>> @a_sync(cache_type='memory', runs_per_minute=60)
            ... async def some_fn():
            ...    return True
            ...
            >>> some_fn(sync=True)
            True

        4. Applied directly to a function:
            >>> some_fn = a_sync(some_existing_function, default='sync')
            >>> some_fn()
            "some return value"

    The decorated function can then be called either synchronously or asynchronously:
        >>> result = some_fn()  # Synchronous call
        >>> result = await some_fn()  # Asynchronous call

    The execution mode can also be explicitly specified during the call:
        >>> result = some_fn(sync=True)  # Force synchronous execution
        >>> result = await some_fn(sync=False)  # Force asynchronous execution

    This decorator is particularly useful for libraries that need to support
    both synchronous and asynchronous usage, or for gradually migrating
    synchronous code to asynchronous without breaking existing interfaces.

    Note:
        If the `coro_fn` argument is passed as 'async' or 'sync', it is treated as the `default` argument,
        and `coro_fn` is set to `None`.

    See Also:
        :class:`ASyncFunction`, :class:`ASyncDecorator`
    """

    # If the dev tried passing a default as an arg instead of a kwarg, ie: @a_sync('sync')...
    if coro_fn in ["async", "sync"]:
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
