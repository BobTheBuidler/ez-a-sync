# mypy: disable-error-code=valid-type
# mypy: disable-error-code=misc
import asyncio

from async_lru import alru_cache

from a_sync import exceptions
from a_sync._typing import *


class CacheKwargs(TypedDict):
    """Typed dictionary for cache keyword arguments."""

    maxsize: Optional[int]
    ttl: Optional[int]
    typed: bool


@overload
def apply_async_memory_cache(**kwargs: Unpack[CacheKwargs]) -> AsyncDecorator[P, T]:
    """Overload for when no coroutine function is provided."""


@overload
def apply_async_memory_cache(
    coro_fn: int, **kwargs: Unpack[CacheKwargs]
) -> AsyncDecorator[P, T]:
    """Overload for when an integer is provided as the coroutine function."""


@overload
def apply_async_memory_cache(
    coro_fn: CoroFn[P, T], **kwargs: Unpack[CacheKwargs]
) -> CoroFn[P, T]:
    """Overload for when a coroutine function is provided."""


@overload
def apply_async_memory_cache(
    coro_fn: Literal[None], **kwargs: Unpack[CacheKwargs]
) -> AsyncDecorator[P, T]:
    """Duplicate overload for when no coroutine function is provided."""


def apply_async_memory_cache(
    coro_fn: Optional[Union[CoroFn[P, T], int]] = None,
    maxsize: Optional[int] = None,
    ttl: Optional[int] = None,
    typed: bool = False,
) -> AsyncDecoratorOrCoroFn[P, T]:
    """Applies an asynchronous LRU cache to a coroutine function.

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

    Returns:
        A decorator if `coro_fn` is None, otherwise the cached coroutine function.
    """
    # Parse Inputs
    if isinstance(coro_fn, int):
        assert maxsize is None
        maxsize = coro_fn
        coro_fn = None

    # Validate
    elif coro_fn is None:
        if maxsize is not None and (not isinstance(maxsize, int) or maxsize <= 0):
            raise TypeError(
                "'lru_cache_maxsize' must be a positive integer or None.", maxsize
            )

    elif not asyncio.iscoroutinefunction(coro_fn):
        raise exceptions.FunctionNotAsync(coro_fn)

    if maxsize == -1:
        maxsize = None

    cache_decorator = alru_cache(maxsize=maxsize, ttl=ttl, typed=typed)
    return cache_decorator if coro_fn is None else cache_decorator(coro_fn)
