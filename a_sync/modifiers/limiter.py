
import asyncio
from typing import Awaitable, Callable, Literal, Optional, Union, overload

from aiolimiter import AsyncLimiter

from a_sync import aliases, exceptions
from a_sync._typing import P, T


@overload
def apply_rate_limit(
    coro_fn: Literal[None] = None,
    runs_per_minute: int = None,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:...
    
@overload
def apply_rate_limit(
    coro_fn: int = None,
    runs_per_minute: Literal[None] = None,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:...
    
@overload
def apply_rate_limit(
    coro_fn: Callable[P, Awaitable[T]] = None,
    runs_per_minute: int = None,
) -> Callable[P, Awaitable[T]]:...
    
@overload
def apply_rate_limit(
    coro_fn: Callable[P, Awaitable[T]] = None,
    runs_per_minute: AsyncLimiter = None,
) -> Callable[P, Awaitable[T]]:...
    
def apply_rate_limit(
    coro_fn: Optional[Union[Callable[P, Awaitable[T]], int]] = None,
    runs_per_minute: Optional[int] = None,
) -> Union[
    Callable[P, Awaitable[T]],
    Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]],
]:
    # Parse Inputs
    if isinstance(coro_fn, int):
        assert runs_per_minute is None
        runs_per_minute = coro_fn
        coro_fn = None
        
    elif coro_fn is None:
        if runs_per_minute is not None and not isinstance(runs_per_minute, int):
            raise TypeError("'runs_per_minute' must be an integer.", runs_per_minute)
        
    elif not asyncio.iscoroutinefunction(coro_fn):
        raise exceptions.FunctionNotAsync(coro_fn)
    
    def rate_limit_decorator(coro_fn: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        limiter = runs_per_minute if isinstance(runs_per_minute, AsyncLimiter) else AsyncLimiter(runs_per_minute) if runs_per_minute else aliases.dummy
        async def rate_limit_wrap(*args: P.args, **kwargs: P.kwargs) -> T:
            async with limiter:
                return await coro_fn(*args, **kwargs)
        return rate_limit_wrap
    
    return rate_limit_decorator if coro_fn is None else rate_limit_decorator(coro_fn)
            
    