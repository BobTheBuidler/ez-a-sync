import asyncio

from a_sync.utils.iterators import (as_yielded, exhaust_iterator,
                                    exhaust_iterators)


__all__ = [
    #"all",
    #"any",
    "as_yielded",
    "exhaust_iterator",
    "exhaust_iterators",
]

async def any(*awaitables) -> bool:
    futs = [asyncio.ensure_future(a) for a in awaitables]
    for fut in asyncio.as_completed(futs):
        try:
            result = bool(await fut)
        except RuntimeError as e:
            if str(e) == "cannot reuse already awaited coroutine":
                raise RuntimeError(str(e), fut) from e
            else:
                raise
        if bool(result):
            for fut in futs:
                fut.cancel()
            return True
    return False
    
async def all(*awaitables) -> bool:
    futs = [asyncio.ensure_future(a) for a in awaitables]
    for fut in asyncio.as_completed(awaitables):
        try:
            result = bool(await fut)
        except RuntimeError as e:
            if str(e) == "cannot reuse already awaited coroutine":
                raise RuntimeError(str(e), fut) from e
            else:
                raise
        if not result:
            for fut in futs:
                fut.cancel()
            return False
    return True
