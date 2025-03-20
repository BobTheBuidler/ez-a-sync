"""
This module provides an enhanced version of :func:`asyncio.gather`.
"""

from a_sync._typing import *
from typing import Any, Awaitable, Dict, List, Mapping, overload

__all__ = ["gather", "gather_mapping"]

class tqdm_asyncio:
    @staticmethod
    async def gather(*args, **kwargs) -> None: ...

Excluder = Callable[[T], bool]

@overload
async def gather(
    awaitables: Mapping[K, Awaitable[V]],
    return_exceptions: bool = False,
    exclude_if: Optional[Excluder[V]] = None,
    tqdm: bool = False,
    **tqdm_kwargs: Any
) -> Dict[K, V]:
    """
    Concurrently awaits a k:v mapping of awaitables and returns the results.

    Args:
        awaitables (Mapping[K, Awaitable[V]]): A mapping of keys to awaitable objects.
        return_exceptions (bool, optional): If True, exceptions are returned as results instead of raising them. Defaults to False.
        exclude_if (Optional[Excluder[V]], optional): A callable that takes a result and returns True if the result should be excluded from the final output. Defaults to None. Note: This is only applied when the input is not a mapping.
        tqdm (bool, optional): If True, enables progress reporting using tqdm. Defaults to False.
        **tqdm_kwargs: Additional keyword arguments for tqdm if progress reporting is enabled.

    Examples:
        Awaiting a mapping of awaitables:

        >>> mapping = {'key1': thing1(), 'key2': thing2()}
        >>> results = await gather(mapping)
        >>> results
        {'key1': 'result', 'key2': 123}

    See Also:
        :func:`asyncio.gather`
    """

@overload
async def gather(
    *awaitables: Awaitable[T],
    return_exceptions: bool = False,
    exclude_if: Optional[Excluder[T]] = None,
    tqdm: bool = False,
    **tqdm_kwargs: Any
) -> List[T]:
    """
    Concurrently awaits a series of awaitable objects and returns the results.

    Args:
        *awaitables (Awaitable[T]): The awaitables to await concurrently.
        return_exceptions (bool, optional): If True, exceptions are returned as results instead of raising them. Defaults to False.
        exclude_if (Optional[Excluder[T]], optional): A callable that takes a result and returns True if the result should be excluded from the final output. Defaults to None.
        tqdm (bool, optional): If True, enables progress reporting using tqdm. Defaults to False.
        **tqdm_kwargs: Additional keyword arguments for tqdm if progress reporting is enabled.

    Examples:
        Awaiting individual awaitables:

        >>> results = await gather(thing1(), thing2())
        >>> results
        ['result', 123]

    See Also:
        :func:`asyncio.gather`
    """

async def gather_mapping(
    mapping: Mapping[K, Awaitable[V]],
    return_exceptions: bool = False,
    exclude_if: Optional[Excluder[V]] = None,
    tqdm: bool = False,
    **tqdm_kwargs: Any
) -> Dict[K, V]:
    """
    Concurrently awaits a mapping of awaitable objects and returns a dictionary of results.

    This function is designed to await a mapping of awaitable objects, where each key-value pair represents a unique awaitable. It enables concurrent execution and gathers results into a dictionary.

    Args:
        mapping (Mapping[K, Awaitable[V]]): A dictionary-like object where keys are of type K and values are awaitable objects of type V.
        return_exceptions (bool, optional): If True, exceptions are returned as results instead of raising them. Defaults to False.
        exclude_if (Optional[Excluder[V]], optional): A callable that takes a result and returns True if the result should be excluded from the final output. Defaults to None. Note: This is not applied when the input is a mapping.
        tqdm (bool, optional): If True, enables progress reporting using tqdm. Defaults to False.
        **tqdm_kwargs: Additional keyword arguments for tqdm if progress reporting is enabled.

    Example:
        The \'results\' dictionary will contain the awaited results, where keys match the keys in the \'mapping\' and values contain the results of the corresponding awaitables.

        >>> mapping = {\'task1\': async_function1(), \'task2\': async_function2(), \'task3\': async_function3()}
        >>> results = await gather_mapping(mapping)
        >>> results
        {\'task1\': "result", \'task2\': 123, \'task3\': None}

    See Also:
        :func:`asyncio.gather`
    """

def cgather(*coros_or_futures: Awaitable[T], return_exceptions: bool = False) -> Awaitable[List[T]]:
    """`asyncio.gather` implemented in c"""
