
import functools
from typing import Callable, Literal, Optional, TypeVar

from typing_extensions import ParamSpec  # type: ignore

from a_sync import _flags, _helpers, _kwargs, exceptions

P = ParamSpec("P")
T = TypeVar("T")


def a_sync(default: Optional[Literal['sync','async']] = None) -> Callable[[Callable[P, T]], Callable[P, T]]:
    f"""
    A coroutine function decorated with this decorator can be called as a sync function by passing a boolean value for any of these kwargs: {_flags.VIABLE_FLAGS}
    """
    if default not in ['async', 'sync', None]:
        if callable(default):
            return a_sync()(default)
        raise ValueError(f"'default' must be either 'sync', 'async', or None. You passed {default}.")
    
    def a_sync_deco(coro_fn: Callable[P, T]) -> Callable[P, T]:  # type: ignore
    
        _helpers._validate_wrapped_fn(coro_fn)

        @functools.wraps(coro_fn)
        def a_sync_wrap(*args: P.args, **kwargs: P.kwargs) -> T:  # type: ignore
            # If a flag was specified in the kwargs, we will defer to it.
            try:
                should_await = _kwargs.is_sync(kwargs, pop_flag=True)
            except exceptions.NoFlagsFound:
                # No flag specified in the kwargs, we will defer to 'default'.
                should_await = True if default == 'sync' else False
            return _helpers._await_if_sync(coro_fn(*args, **kwargs), should_await)
        return a_sync_wrap
    return a_sync_deco
