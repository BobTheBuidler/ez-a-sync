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
    """
    Asynchronously evaluates whether any of the given awaitables evaluates to True.

    This function takes multiple awaitable objects and returns True if at least one of them evaluates to True. It cancels 
    the remaining awaitables once a True result is found.

    Args:
        *awaitables: A variable length list of awaitable objects.

    Returns:
        bool: True if any of the awaitables evaluates to True, otherwise False.
    """
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
    """
    Asynchronously evaluates whether all of the given awaitables evaluate to True.

    This function takes multiple awaitable objects and returns True if all of them evaluate to True. It cancels 
    the remaining awaitables once a False result is found.

    Args:
        *awaitables: A variable length list of awaitable objects.

    Returns:
        bool: True if all of the awaitables evaluate to True, otherwise False.
    """
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
