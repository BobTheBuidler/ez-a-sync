
import asyncio

from aiolimiter import AsyncLimiter

from a_sync import aliases, exceptions
from a_sync._typing import *


@overload
def apply_rate_limit(
    coro_fn: Literal[None],
    runs_per_minute: int,
) -> AsyncDecorator[P, T]:...
    
@overload
def apply_rate_limit(
    coro_fn: int,
    runs_per_minute: Literal[None],
) -> AsyncDecorator[P, T]:...
    
@overload
def apply_rate_limit(
    coro_fn: CoroFn[P, T],
    runs_per_minute: Union[int, AsyncLimiter],
) -> CoroFn[P, T]:...
    
def apply_rate_limit(
    coro_fn: Optional[Union[CoroFn[P, T], int]] = None,
    runs_per_minute: Optional[Union[int, AsyncLimiter]] = None,
) -> AsyncDecoratorOrCoroFn[P, T]:
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
    
    def rate_limit_decorator(coro_fn: CoroFn[P, T]) -> CoroFn[P, T]:
        limiter = runs_per_minute if isinstance(runs_per_minute, AsyncLimiter) else AsyncLimiter(runs_per_minute) if runs_per_minute else aliases.dummy
        async def rate_limit_wrap(*args: P.args, **kwargs: P.kwargs) -> T:
            async with limiter:  # type: ignore [attr-defined]
                return await coro_fn(*args, **kwargs)
        return rate_limit_wrap
    
    return rate_limit_decorator if coro_fn is None else rate_limit_decorator(coro_fn)
            
    