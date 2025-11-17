"""
This module provides an enhanced version of :func:`asyncio.gather`.

It defines overloads for concurrently awaiting awaitable objects. There are separate overloads for accepting a mapping of awaitables and for accepting a sequence of awaitables. In the mapping overload, note that the `exclude_if` parameter is ignored (i.e. it is not applied) because the mapping itself determines the keys and values.
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
    Concurrently awaits a mapping of awaitable objects and returns a dictionary of results.

    Args:
        awaitables (Mapping[K, Awaitable[V]]): A mapping where each key is associated with an awaitable object.
        return_exceptions (bool, optional): If True, exceptions raised during awaiting are returned as results instead of being raised. Defaults to False.
        exclude_if (Optional[Excluder[V]], optional): A callable that takes a result and returns True if the result should be excluded from the final output. Defaults to None.
            **Note:** For mapping inputs, this parameter is ignored.
        tqdm (bool, optional): If True, enables progress reporting using tqdm. Defaults to False.
        **tqdm_kwargs: Additional keyword arguments for tqdm when progress reporting is enabled.

    Examples:
        Awaiting a mapping of awaitable objects:

        >>> mapping = {'key1': thing1(), 'key2': thing2()}
        >>> results = await gather(mapping)
        >>> print(results)
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
    Concurrently awaits a series of awaitable objects and returns a list of results.

    Args:
        *awaitables (Awaitable[T]): The awaitable objects to be awaited concurrently.
        return_exceptions (bool, optional): If True, exceptions raised during awaiting are returned as results instead of being raised. Defaults to False.
        exclude_if (Optional[Excluder[T]], optional): A callable that takes a result and returns True if the result should be excluded from the final output. Defaults to None.
        tqdm (bool, optional): If True, enables progress reporting using tqdm. Defaults to False.
        **tqdm_kwargs: Additional keyword arguments for tqdm when progress reporting is enabled.

    Examples:
        Awaiting individual awaitable objects:

        >>> results = await gather(thing1(), thing2())
        >>> print(results)
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

    This function awaits each awaitable associated with the keys provided in the input mapping.
    The final dictionary retains the same keys as the input mapping and maps each key to the result
    of its corresponding awaitable. The exclude_if parameter is not applied in this overload.

    Args:
        mapping (Mapping[K, Awaitable[V]]): A mapping with keys of type K and corresponding awaitable objects of type V.
        return_exceptions (bool, optional): If True, exceptions raised during awaiting are returned as results
            instead of being raised. Defaults to False.
        exclude_if (Optional[Excluder[V]], optional): A callable that takes a result and returns True if the result
            should be excluded from the final output. Defaults to None. (This parameter is ignored for mapping inputs.)
        tqdm (bool, optional): If True, enables progress reporting using tqdm. Defaults to False.
        **tqdm_kwargs: Additional keyword arguments for tqdm when progress reporting is enabled.

    Examples:
        Awaiting a mapping of awaitable objects:

        >>> mapping = {
        ...     'task1': async_function1(),
        ...     'task2': async_function2(),
        ...     'task3': async_function3(),
        ... }
        >>> results = await gather_mapping(mapping)
        >>> print(results)
        {'task1': "result", 'task2': 123, 'task3': None}

    See Also:
        :func:`asyncio.gather`
    """

def cgather(*coros_or_futures: Awaitable[T], return_exceptions: bool = False) -> Awaitable[List[T]]:
    """`asyncio.gather` implemented in C"""