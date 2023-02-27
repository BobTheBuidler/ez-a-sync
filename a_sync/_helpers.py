
import asyncio
from inspect import getfullargspec
from typing import Awaitable, Callable, Literal, TypeVar, Union, overload

from async_property.base import AsyncPropertyDescriptor
from async_property.cached import AsyncCachedPropertyDescriptor

from a_sync import _flags

T = TypeVar("T")


def _validate_wrapped_fn(fn: Callable) -> None:
    """Ensures 'fn' is an appropriate function for wrapping with a_sync."""
    if isinstance(fn, (AsyncPropertyDescriptor, AsyncCachedPropertyDescriptor)):
        return # These are always valid
    if not asyncio.iscoroutinefunction(fn):
        raise TypeError(f"{fn} must be a coroutine function.")
    fn_args = getfullargspec(fn)[0]
    for flag in _flags.VIABLE_FLAGS:
        if flag in fn_args:
            raise RuntimeError(f"{fn} must not have any arguments with the following names: {_flags.VIABLE_FLAGS}")


@overload
def _await_if_sync(awaitable: Awaitable[T], sync: Literal[True]) -> T:
    ...

@overload
def _await_if_sync(awaitable: Awaitable[T], sync: Literal[False]) -> Awaitable[T]:
    ...

def _await_if_sync(awaitable: Awaitable[T], sync: bool) -> Union[T, Awaitable[T]]:
    """
    If 'sync' is True, awaits the awaitable and returns the return value.
    If 'sync' is False, simply returns the awaitable.
    """
    if sync:
        try:
            return asyncio.get_event_loop().run_until_complete(awaitable)
        except RuntimeError as e:
            if "is already running" in str(e):
                raise RuntimeError(str(e), f"You may want to make this an async function by setting one of the following kwargs: {_flags.VIABLE_FLAGS}")
            raise
    else:
        return awaitable
