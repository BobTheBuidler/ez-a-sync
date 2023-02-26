
import functools
from typing import Callable, TypeVar, Literal, Optional

from typing_extensions import ParamSpec  # type: ignore

from a_sync import _helpers

P = ParamSpec("P")
T = TypeVar("T")


def a_sync(default: Optional[Literal['sync','async']] = None) -> Callable[[Callable[P, T]], Callable[P, T]]:
    f"""
    A coroutine function decorated with this decorator can be called as a sync function by passing a boolean value for any of these kwargs: {_helpers._flag_name_options}
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
            for flag in _helpers._flag_name_options:
                if flag in kwargs:
                    val = kwargs.pop(flag)
                    if not isinstance(val, bool):
                        raise TypeError(f"'{flag}' must be boolean. You passed {val}.")
                    return _helpers._await_if_sync(
                        coro_fn(*args, **kwargs),
                        val if flag == 'sync' else not val
                    )
                
            # No flag specified in the kwargs, we will defer to 'default'.
            return _helpers._await_if_sync(
                coro_fn(*args, **kwargs),
                True if default == 'sync' else False
            )
        return a_sync_wrap
    return a_sync_deco
