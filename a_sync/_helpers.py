
import asyncio
import functools
from concurrent.futures import Executor
from inspect import getfullargspec

from async_property.base import \
    AsyncPropertyDescriptor  # type: ignore [import]
from async_property.cached import \
    AsyncCachedPropertyDescriptor  # type: ignore [import]

from a_sync import _flags
from a_sync._typing import *
from a_sync.exceptions import (ASyncRuntimeError, KwargsUnsupportedError,
                               SyncModeInAsyncContextError)


def get_event_loop() -> asyncio.AbstractEventLoop:
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError as e: # Necessary for use with multi-threaded applications.
        if not str(e).startswith("There is no current event loop in thread"):
            raise e
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop
    
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

def _await(awaitable: Awaitable[T]) -> T:
    try:
        return get_event_loop().run_until_complete(awaitable)
    except RuntimeError as e:
        if str(e) == "This event loop is already running":
            raise SyncModeInAsyncContextError from e
        raise ASyncRuntimeError(e) from e

def _asyncify(func: SyncFn[P, T], executor: Executor) -> CoroFn[P, T]:  # type: ignore [misc]
    @functools.wraps(func)
    async def _asyncify_wrap(*args: P.args, **kwargs: P.kwargs) -> T:
        return await asyncio.futures.wrap_future(
            executor.submit(func, *args, **kwargs), 
            loop=get_event_loop(),
        )
    return _asyncify_wrap
