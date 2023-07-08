# mypy: disable-error-code=valid-type
# mypy: disable-error-code=misc
import asyncio

from a_sync import exceptions
from a_sync._typing import *
from a_sync.modifiers.cache.memory import apply_async_memory_cache


class CacheArgs(TypedDict):
    cache_type: CacheType
    cache_typed: bool
    ram_cache_maxsize: Optional[int]
    ram_cache_ttl: Optional[int]

@overload
def apply_async_cache(
    coro_fn: Literal[None],
    **modifiers: Unpack[CacheArgs],
) -> AsyncDecorator[P, T]:...
    
@overload
def apply_async_cache(
    coro_fn: int,
    **modifiers: Unpack[CacheArgs],
) -> AsyncDecorator[P, T]:...
    
@overload
def apply_async_cache(
    coro_fn: CoroFn[P, T],
    **modifiers: Unpack[CacheArgs],
) -> CoroFn[P, T]:...
    
def apply_async_cache(
    coro_fn: Union[CoroFn[P, T], CacheType, int] = None,
    cache_type: CacheType = 'memory',
    cache_typed: bool = False,
    ram_cache_maxsize: Optional[int] = None,
    ram_cache_ttl: Optional[int] = None,
) -> AsyncDecoratorOrCoroFn[P, T]:
    
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