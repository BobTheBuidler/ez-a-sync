"""
This module initializes the utility functions for the a_sync library, including functions for handling asynchronous
iterators and implementing asynchronous versions of the built-in any and all functions.
"""

from asyncio import as_completed, ensure_future
from typing import TYPE_CHECKING, Any, Final, final

from a_sync.utils.iterators import as_yielded, exhaust_iterator, exhaust_iterators

if TYPE_CHECKING:
    from _typeshed import SupportsBool
    from asyncio.tasks import _FutureLike


__all__ = [
    # "all",
    # "any",
    "as_yielded",
    "exhaust_iterator",
    "exhaust_iterators",
]


async def any(*awaitables: "_FutureLike[SupportsBool]") -> bool:
    """
    Asynchronously evaluates whether any of the given awaitables evaluates to True.

    This function returns True if any element in the asynchronous iterable is truthy.
    It short-circuits on the first truthy value. If the iterable is empty, it returns False.

    Args:
        *awaitables: A variable length list of awaitable objects.

    Returns:
        bool: True if any element is truthy, False if all are falsy or the iterable is empty.

    Example:
        >>> async def is_odd(x):
        ...     await asyncio.sleep(0.1)  # Simulate some async work
        ...     return x % 2 != 0
        ...
        >>> numbers = [2, 4, 6, 7]
        >>> result = await any(*[is_odd(x) for x in numbers])
        >>> result
        True
        >>> numbers = [2, 4, 6, 8]
        >>> result = await any(*[is_odd(x) for x in numbers])
        >>> result
        False

    Note:
        This function will stop iterating as soon as it encounters a truthy value.
    """
    futs = list(map(ensure_future, awaitables))
    for fut in as_completed(futs):
        try:
            result = await fut
        except RuntimeError as e:
            if str(e) == "cannot reuse already awaited coroutine":
                raise RuntimeError(str(e), fut) from e
            else:
                raise
        if bool(result):
            cancel_msg = CancelMessage("[a_sync.any] exiting early due to Truthy result", result)
            for fut in futs:
                fut.cancel(cancel_msg)
            return True
    return False


async def all(*awaitables: "_FutureLike[SupportsBool]") -> bool:
    """
    Asynchronously evaluates whether all of the given awaitables evaluate to True.

    This function takes multiple awaitable objects and returns True if all of them evaluate to True. It cancels
    the remaining awaitables once a False result is found.

    Args:
        *awaitables: A variable length list of awaitable objects.

    Returns:
        bool: True if all elements are truthy or the iterable is empty, False otherwise.

    Example:
        >>> async def is_even(x):
        ...    return x % 2 == 0
        ...
        >>> numbers = [2, 4, 6, 8]
        >>> result = await all(*[is_even(x) for x in numbers])
        >>> result
        True
        >>> numbers = [2, 3, 4, 6]
        >>> result = await all(*[is_even(x) for x in numbers])
        >>> result
        False
    """
    futs = list(map(ensure_future, awaitables))
    for fut in as_completed(futs):
        try:
            result = await fut
        except RuntimeError as e:
            if str(e) == "cannot reuse already awaited coroutine":
                raise RuntimeError(str(e), fut) from e
            else:
                raise
        if not bool(result):
            cancel_msg = CancelMessage("[a_sync.all] exiting early due to Falsey result", result)
            for fut in futs:
                fut.cancel(cancel_msg)
            return False
    return True


@final
class CancelMessage:
    """
    This class wraps a cancel message + result pair so that we can
    pass it around freely as one object but only construct the
    string representation when required by something downstream.
    """

    def __init__(self, message: str, result: Any) -> None:
        self.message: Final = message
        self.result: Final = result

    def __repr__(self) -> str:
        return f"CancelMessage('{str(self)}')"

    def __str__(self) -> str:
        return f"{message}: {result!r}"
