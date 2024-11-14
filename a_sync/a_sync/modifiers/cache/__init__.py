# mypy: disable-error-code=valid-type
# mypy: disable-error-code=misc
import asyncio

from a_sync import exceptions
from a_sync._typing import *
from a_sync.a_sync.modifiers.cache.memory import apply_async_memory_cache


class CacheArgs(TypedDict):
    """Typed dictionary for cache arguments."""

    cache_type: CacheType
    """The type of cache to use. Currently, only 'memory' is implemented."""

    cache_typed: bool
    """Whether to consider types for cache keys."""

    ram_cache_maxsize: Optional[int]
    """The maximum size for the LRU cache."""

    ram_cache_ttl: Optional[int]
    """The time-to-live for items in the LRU cache."""


@overload
def apply_async_cache(
    **modifiers: Unpack[CacheArgs],
) -> AsyncDecorator[P, T]:
    """Creates a decorator to apply an asynchronous cache.

    This overload is used when no coroutine function is provided. The returned
    decorator can be applied to a coroutine function later.

    Args:
        **modifiers: Cache configuration options such as `cache_type`, `cache_typed`, `ram_cache_maxsize`, and `ram_cache_ttl`.

    Examples:
        >>> @apply_async_cache(cache_type='memory', ram_cache_maxsize=100)
        ... async def my_function():
        ...     pass

    See Also:
        :func:`apply_async_memory_cache`
    """


@overload
def apply_async_cache(
    coro_fn: int,
    **modifiers: Unpack[CacheArgs],
) -> AsyncDecorator[P, T]:
    """Creates a decorator with `ram_cache_maxsize` set by an integer.

    This overload is used when an integer is provided as the first argument,
    which sets the `ram_cache_maxsize` for the cache. The returned decorator
    can be applied to a coroutine function later.

    Args:
        coro_fn: An integer to set as the max size for the cache.
        **modifiers: Additional cache configuration options.

    Examples:
        >>> @apply_async_cache(100, cache_type='memory')
        ... async def my_function():
        ...     pass

    See Also:
        :func:`apply_async_memory_cache`
    """


@overload
def apply_async_cache(
    coro_fn: CoroFn[P, T],
    **modifiers: Unpack[CacheArgs],
) -> CoroFn[P, T]:
    """Applies an asynchronous cache directly to a coroutine function.

    This overload is used when a coroutine function is provided. The cache is
    applied directly to the function.

    Args:
        coro_fn: The coroutine function to be cached.
        **modifiers: Cache configuration options such as `cache_type`, `cache_typed`, `ram_cache_maxsize`, and `ram_cache_ttl`.

    Examples:
        >>> async def my_function():
        ...     pass
        >>> cached_function = apply_async_cache(my_function, cache_type='memory', ram_cache_maxsize=100)

    See Also:
        :func:`apply_async_memory_cache`
    """


def apply_async_cache(
    coro_fn: Union[CoroFn[P, T], CacheType, int] = None,
    cache_type: CacheType = "memory",
    cache_typed: bool = False,
    ram_cache_maxsize: Optional[int] = None,
    ram_cache_ttl: Optional[int] = None,
) -> AsyncDecoratorOrCoroFn[P, T]:
    """Applies an asynchronous cache to a coroutine function.

    This function can be used to apply a cache to a coroutine function, either by passing the function directly or by using it as a decorator. The cache type is currently limited to 'memory'. If an unsupported cache type is specified, a `NotImplementedError` is raised.

    Args:
        coro_fn: The coroutine function to apply the cache to, or an integer to set as the max size.
        cache_type: The type of cache to use. Currently, only 'memory' is implemented.
        cache_typed: Whether to consider types for cache keys.
        ram_cache_maxsize: The maximum size for the LRU cache. If set to an integer, it overrides coro_fn.
        ram_cache_ttl: The time-to-live for items in the LRU cache.

    Raises:
        TypeError: If 'ram_cache_maxsize' is not an integer or None.
        FunctionNotAsync: If the provided function is not asynchronous.
        NotImplementedError: If an unsupported cache type is specified.

    Examples:
        >>> @apply_async_cache(cache_type='memory', ram_cache_maxsize=100)
        ... async def my_function():
        ...     pass

        >>> async def my_function():
        ...     pass
        >>> cached_function = apply_async_cache(my_function, cache_type='memory', ram_cache_maxsize=100)

        >>> @apply_async_cache(100, cache_type='memory')
        ... async def another_function():
        ...     pass

    See Also:
        :func:`apply_async_memory_cache`
    """

    # Parse Inputs
    if isinstance(coro_fn, int):
        assert ram_cache_maxsize is None
        ram_cache_maxsize = coro_fn
        coro_fn = None

    # Validate
    elif coro_fn is None:
        if ram_cache_maxsize is not None and not isinstance(ram_cache_maxsize, int):
            raise TypeError(
                "'lru_cache_maxsize' must be an integer or None.", ram_cache_maxsize
            )
    elif not asyncio.iscoroutinefunction(coro_fn):
        raise exceptions.FunctionNotAsync(coro_fn)

    if cache_type == "memory":
        cache_decorator = apply_async_memory_cache(
            maxsize=ram_cache_maxsize, ttl=ram_cache_ttl, typed=cache_typed
        )
        return cache_decorator if coro_fn is None else cache_decorator(coro_fn)
    elif cache_type == "disk":
        pass
    raise NotImplementedError(f"cache_type: {cache_type}")
