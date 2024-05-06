
import asyncio
import functools
from concurrent.futures import Executor

import a_sync.asyncio
from a_sync import exceptions
from a_sync._typing import *


def _await(awaitable: Awaitable[T]) -> T:
    try:
        return a_sync.asyncio.get_event_loop().run_until_complete(awaitable)
    except RuntimeError as e:
        if str(e) == "This event loop is already running":
            raise exceptions.SyncModeInAsyncContextError from None
        raise

def _asyncify(func: SyncFn[P, T], executor: Executor) -> CoroFn[P, T]:  # type: ignore [misc]
    from a_sync.a_sync.function import ASyncFunction
    if asyncio.iscoroutinefunction(func) or isinstance(func, ASyncFunction):
        raise exceptions.FunctionNotSync(func)
    @functools.wraps(func)
    async def _asyncify_wrap(*args: P.args, **kwargs: P.kwargs) -> T:
        return await asyncio.futures.wrap_future(
            executor.submit(func, *args, **kwargs), 
            loop=a_sync.asyncio.get_event_loop(),
        )
    return _asyncify_wrap
