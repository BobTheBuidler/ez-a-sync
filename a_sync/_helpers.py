
import asyncio
import functools
from inspect import getfullargspec

from async_property.base import \
    AsyncPropertyDescriptor  # type: ignore [import]
from async_property.cached import \
    AsyncCachedPropertyDescriptor  # type: ignore [import]

from a_sync import _flags
from a_sync._typing import *


def _validate_wrapped_fn(fn: Callable) -> None:
    """Ensures 'fn' is an appropriate function for wrapping with a_sync."""
    if isinstance(fn, (AsyncPropertyDescriptor, AsyncCachedPropertyDescriptor)):
        return # These are always valid
    if not callable(fn):
        raise TypeError(f'Input is not callable. Unable to decorate {fn}')
    fn_args = getfullargspec(fn)[0]
    for flag in _flags.VIABLE_FLAGS:
        if flag in fn_args:
            raise RuntimeError(f"{fn} must not have any arguments with the following names: {_flags.VIABLE_FLAGS}")

running_event_loop_msg = f"You may want to make this an async function by setting one of the following kwargs: {_flags.VIABLE_FLAGS}"

def _await(awaitable: Awaitable[T]) -> T:
    try:
        return asyncio.get_event_loop().run_until_complete(awaitable)
    except RuntimeError as e:
        if str(e) == "This event loop is already running":
            raise RuntimeError(str(e), running_event_loop_msg)
        raise

def _asyncify(func: SyncFn[P, T], executor: Executor) -> CoroFn[P, T]:
    @functools.wraps(func)
    async def _asyncify_wrap(*args: P.args, **kwargs: P.kwargs) -> T:
        return await asyncio.get_event_loop().run_in_executor(executor, func, *args, **kwargs)
    return _asyncify_wrap
