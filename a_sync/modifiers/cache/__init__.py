
import asyncio

from a_sync import exceptions
from a_sync._typing import *
from a_sync.modifiers.cache.memory import apply_async_memory_cache


class CacheArgs(TypedDict):
    cache_type: Literal['memory', None]
    cache_typed: bool
    ram_cache_maxsize: Optional[int]
    ram_cache_ttl: Optional[int]

@overload
def apply_async_cache(
    coro_fn: Literal[None] = None,
    **modifiers: Unpack[CacheArgs],
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:...
    
@overload
def apply_async_cache(
    coro_fn: int = None,
    **modifiers: Unpack[CacheArgs],
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:...
    
@overload
def apply_async_cache(
    coro_fn: Callable[P, Awaitable[T]] = None,
    **modifiers: Unpack[CacheArgs],
) -> Callable[P, Awaitable[T]]:...
    
def apply_async_cache(
    coro_fn: Union[Callable[P, Awaitable[T]], Literal['memory']] = None,
    cache_type: Literal['memory'] = 'memory',
    cache_typed: bool = False,
    ram_cache_maxsize: Optional[int] = None,
    ram_cache_ttl: Optional[int] = None,
) -> Union[
    Callable[P, Awaitable[T]],
    Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]],
]:
    
    # Parse Inputs
    if isinstance(coro_fn, int):
        assert ram_cache_maxsize is None
        ram_cache_maxsize = coro_fn
        coro_fn = None
    
    # Validate 
    elif coro_fn is None:
        if ram_cache_maxsize is not None and not isinstance(ram_cache_maxsize, int):
            raise TypeError("'lru_cache_maxsize' must be an integer or None.", ram_cache_maxsize)
    elif not asyncio.iscoroutinefunction(coro_fn):
        raise exceptions.FunctionNotAsync(coro_fn)
    
    if cache_type == 'memory':
        cache_decorator = apply_async_memory_cache(maxsize=ram_cache_maxsize, ttl=ram_cache_ttl, typed=cache_typed)
        return cache_decorator if coro_fn is None else cache_decorator(coro_fn)
    elif cache_type == 'disk':
        pass
    raise NotImplementedError(f"cache_type: {cache_type}")