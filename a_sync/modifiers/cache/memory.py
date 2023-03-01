

import asyncio
from typing import Awaitable, Callable, Literal, Optional, Union, overload

from async_lru import alru_cache

from a_sync import exceptions
from a_sync._typing import P, T



@overload
def apply_async_memory_cache(
    coro_fn: Literal[None],
    maxsize: Literal[None],
    ttl: int,
    typed: bool,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:...
    
@overload
def apply_async_memory_cache(
    coro_fn: int,
    maxsize: Literal[None],
    ttl: Optional[int],
    typed: bool = False,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:...
    
@overload
def apply_async_memory_cache(
    coro_fn: Callable[P, Awaitable[T]],
    maxsize: int,
    ttl: Optional[int] = None,
    typed: bool = False,
) -> Callable[P, Awaitable[T]]:...

@overload
def apply_async_memory_cache(
    coro_fn: Literal[None],
    maxsize: Optional[int],
    ttl: Optional[int],
    typed: bool,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:...

def apply_async_memory_cache(
    coro_fn: Optional[Union[Callable[P, Awaitable[T]], int]] = None,
    maxsize: Optional[int] = None,
    ttl: Optional[int] = None,
    typed: bool = False,
) -> Union[
    Callable[P, Awaitable[T]],
    Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]],
]:
    # Parse Inputs
    if isinstance(coro_fn, int):
        assert maxsize is None
        maxsize = coro_fn
        coro_fn = None
    
    # Validate 
    elif coro_fn is None:
        if maxsize is not None and not isinstance(maxsize, int):
            raise TypeError("'lru_cache_maxsize' must be an integer or None.", maxsize)
    elif not asyncio.iscoroutinefunction(coro_fn):
        raise exceptions.FunctionNotAsync(coro_fn)
    
    cache_decorator = alru_cache(maxsize=maxsize, ttl=ttl, typed=typed)
    return cache_decorator if coro_fn is None else cache_decorator(coro_fn)
