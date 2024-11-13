# mypy: disable-error-code=valid-type
# mypy: disable-error-code=misc
import asyncio

from a_sync import exceptions
from a_sync._typing import *
from a_sync.a_sync.modifiers.cache.memory import apply_async_memory_cache


class CacheArgs(TypedDict):
    """Typed dictionary for cache arguments."""

    cache_type: CacheType
    cache_typed: bool
    ram_cache_maxsize: Optional[int]
    ram_cache_ttl: Optional[int]


@overload
def apply_async_cache(
    **modifiers: Unpack[CacheArgs],
) -> AsyncDecorator[P, T]:
    """Overload for when no coroutine function is provided."""


@overload
def apply_async_cache(
    coro_fn: int,
    **modifiers: Unpack[CacheArgs],
) -> AsyncDecorator[P, T]:
    """Overload for when an integer is provided as the coroutine function."""


@overload
def apply_async_cache(
    coro_fn: CoroFn[P, T],
    **modifiers: Unpack[CacheArgs],
) -> CoroFn[P, T]:
    """Overload for when a coroutine function is provided."""


def apply_async_cache(
    coro_fn: Union[CoroFn[P, T], CacheType, int] = None,
    cache_type: CacheType = "memory",
    cache_typed: bool = False,
    ram_cache_maxsize: Optional[int] = None,
    ram_cache_ttl: Optional[int] = None,
) -> AsyncDecoratorOrCoroFn[P, T]:
    """Applies an asynchronous cache to a coroutine function.

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

    Returns:
        A decorator or the decorated coroutine function.
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
