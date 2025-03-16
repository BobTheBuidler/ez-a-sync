# mypy: disable-error-code=valid-type
# mypy: disable-error-code=misc

from async_lru import alru_cache

from a_sync._typing import *
from a_sync.exceptions import FunctionNotAsync


class CacheKwargs(TypedDict):
    """Typed dictionary for cache keyword arguments."""

    maxsize: Optional[int]
    ttl: Optional[int]
    typed: bool


@overload
def apply_async_memory_cache(**kwargs: Unpack[CacheKwargs]) -> AsyncDecorator[P, T]:
    """
    Creates a decorator to apply an asynchronous LRU cache.

    This overload is used when no coroutine function is provided. The returned
    decorator can be applied to a coroutine function later.

    Args:
        **kwargs: Keyword arguments for cache configuration, including maxsize,
            ttl, and typed.

    Examples:
        >>> @apply_async_memory_cache(maxsize=128, ttl=60)
        ... async def fetch_data():
        ...     pass

    See Also:
        - :func:`alru_cache` for the underlying caching mechanism.
    """


@overload
def apply_async_memory_cache(coro_fn: int, **kwargs: Unpack[CacheKwargs]) -> AsyncDecorator[P, T]:
    """Creates a decorator with maxsize set by an integer.

    This overload is used when an integer is provided as the coroutine function,
    which sets the maxsize for the cache. The returned decorator can be applied
    to a coroutine function later.

    Args:
        coro_fn: An integer to set as maxsize for the cache.
        **kwargs: Additional keyword arguments for cache configuration, including
            ttl and typed.

    Examples:
        >>> # This usage is not supported
        >>> apply_async_memory_cache(128, ttl=60)

    See Also:
        - :func:`apply_async_memory_cache` for correct usage.
    """


@overload
def apply_async_memory_cache(coro_fn: CoroFn[P, T], **kwargs: Unpack[CacheKwargs]) -> CoroFn[P, T]:
    """
    Applies an asynchronous LRU cache to a provided coroutine function.

    This overload is used when a coroutine function is provided. The cache is
    applied directly to the function.

    Args:
        coro_fn: The coroutine function to be cached.
        **kwargs: Keyword arguments for cache configuration, including maxsize,
            ttl, and typed.

    Examples:
        >>> async def fetch_data():
        ...     pass
        >>> cached_fetch = apply_async_memory_cache(fetch_data, maxsize=128, ttl=60)

    See Also:
        - :func:`alru_cache` for the underlying caching mechanism.
    """


@overload
def apply_async_memory_cache(
    coro_fn: Literal[None], **kwargs: Unpack[CacheKwargs]
) -> AsyncDecorator[P, T]:
    """
    Creates a decorator to apply an asynchronous LRU cache.

    This duplicate overload is used when no coroutine function is provided. The
    returned decorator can be applied to a coroutine function later.

    Args:
        coro_fn: None, indicating no coroutine function is provided.
        **kwargs: Keyword arguments for cache configuration, including maxsize,
            ttl, and typed.

    Examples:
        >>> @apply_async_memory_cache(maxsize=128, ttl=60)
        ... async def fetch_data():
        ...     pass

    See Also:
        - :func:`alru_cache` for the underlying caching mechanism.
    """


def apply_async_memory_cache(
    coro_fn: Optional[Union[CoroFn[P, T], int]] = None,
    maxsize: Optional[int] = None,
    ttl: Optional[int] = None,
    typed: bool = False,
) -> AsyncDecoratorOrCoroFn[P, T]:
    """
    Applies an asynchronous LRU cache to a coroutine function.

    This function uses the `alru_cache` from the `async_lru` library to cache
    the results of an asynchronous coroutine function. The cache can be configured
    with a maximum size, a time-to-live (TTL), and whether the cache keys should
    be typed.

    Args:
        coro_fn: The coroutine function to be cached, or an integer to set as maxsize.
        maxsize: The maximum size of the cache. If set to -1, it is converted to None,
            making the cache unbounded.
        ttl: The time-to-live for cache entries in seconds. If None, entries do not expire.
        typed: Whether to consider the types of arguments as part of the cache key.

    Raises:
        TypeError: If `maxsize` is not a positive integer or None when `coro_fn` is None.
        exceptions.FunctionNotAsync: If `coro_fn` is not an asynchronous function.

    Examples:
        >>> @apply_async_memory_cache(maxsize=128, ttl=60)
        ... async def fetch_data():
        ...     pass

        >>> async def fetch_data():
        ...     pass
        >>> cached_fetch = apply_async_memory_cache(fetch_data, maxsize=128, ttl=60)

    See Also:
        - :func:`alru_cache` for the underlying caching mechanism.
    """
    # Parse Inputs
    if isinstance(coro_fn, int):
        assert maxsize is None
        maxsize = coro_fn
        coro_fn = None

    # Validate
    elif coro_fn is None:
        if maxsize not in [None, -1] and (not isinstance(maxsize, int) or maxsize <= 0):
            raise TypeError("'lru_cache_maxsize' must be a positive integer or None.", maxsize)

    elif not iscoroutinefunction(coro_fn):
        raise FunctionNotAsync(coro_fn)

    if maxsize == -1:
        maxsize = None

    cache_decorator = alru_cache(maxsize=maxsize, ttl=ttl, typed=typed)
    return cache_decorator if coro_fn is None else cache_decorator(coro_fn)
