"""
This module provides an enhanced version of :func:`asyncio.gather`.
"""

import asyncio
from typing import Any, Awaitable, Dict, List, Mapping, TypeVar, Union, overload

try:
    from tqdm.asyncio import tqdm_asyncio
except ImportError as e:

    class tqdm_asyncio:  # type: ignore [no-redef]
        async def gather(*args, **kwargs):
            raise ImportError(
                "You must have tqdm installed in order to use this feature"
            )


from a_sync._typing import *
from a_sync.asyncio.as_completed import as_completed_mapping, _exc_wrap


Excluder = Callable[[T], bool]


@overload
async def gather(
    *awaitables: Mapping[K, Awaitable[V]],
    return_exceptions: bool = False,
    exclude_if: Optional[Excluder[V]] = None,
    tqdm: bool = False,
    **tqdm_kwargs: Any,
) -> Dict[K, V]: ...
@overload
async def gather(
    *awaitables: Awaitable[T],
    return_exceptions: bool = False,
    exclude_if: Optional[Excluder[T]] = None,
    tqdm: bool = False,
    **tqdm_kwargs: Any,
) -> List[T]: ...
async def gather(
    *awaitables: Union[Awaitable[T], Mapping[K, Awaitable[V]]],
    return_exceptions: bool = False,
    exclude_if: Optional[Excluder[T]] = None,
    tqdm: bool = False,
    **tqdm_kwargs: Any,
) -> Union[List[T], Dict[K, V]]:
    """
    Concurrently awaits a list of awaitable objects or a mapping of awaitables and returns the results.

    This function extends Python's asyncio.gather, providing additional features for handling either individual awaitable objects or a mapping of awaitables.

    Differences from asyncio.gather:
    - Uses type hints for use with static type checkers.
    - Supports gathering either individual awaitables or a k:v mapping of awaitables.
    - Provides progress reporting using tqdm if 'tqdm' is set to True.
    - Allows exclusion of results based on a condition using the 'exclude_if' parameter.

    Args:
        *awaitables: The awaitables to await concurrently. It can be a list of individual awaitables or a mapping of awaitables.
        return_exceptions: If True, exceptions are returned as results instead of raising them. Defaults to False.
        exclude_if: A callable that takes a result and returns True if the result should be excluded from the final output. Defaults to None.
        tqdm: If True, enables progress reporting using tqdm. Defaults to False.
        **tqdm_kwargs: Additional keyword arguments for tqdm if progress reporting is enabled.

    Examples:
        Awaiting individual awaitables:

        - Results will be a list containing the result of each awaitable in sequential order.

        >>> results = await gather(thing1(), thing2())
        >>> results
        ['result', 123]

        Awaiting a mapping of awaitables:

        - Results will be a dictionary with 'key1' mapped to the result of thing1() and 'key2' mapped to the result of thing2.

        >>> mapping = {'key1': thing1(), 'key2': thing2()}
        >>> results = await gather(mapping)
        >>> results
        {'key1': 'result', 'key2': 123}
    """
    is_mapping = _is_mapping(awaitables)
    results = await (
        gather_mapping(
            awaitables[0],
            return_exceptions=return_exceptions,
            exclude_if=exclude_if,
            tqdm=tqdm,
            **tqdm_kwargs,
        )
        if is_mapping
        else (
            tqdm_asyncio.gather(
                *(
                    (_exc_wrap(a) for a in awaitables)
                    if return_exceptions
                    else awaitables
                ),
                **tqdm_kwargs,
            )
            if tqdm
            else asyncio.gather(*awaitables, return_exceptions=return_exceptions)
        )  # type: ignore [arg-type]
    )
    if exclude_if and not is_mapping:
        results = [r for r in results if not exclude_if(r)]
    return results


async def gather_mapping(
    mapping: Mapping[K, Awaitable[V]],
    return_exceptions: bool = False,
    exclude_if: Optional[Excluder[V]] = None,
    tqdm: bool = False,
    **tqdm_kwargs: Any,
) -> Dict[K, V]:
    """
    Concurrently awaits a mapping of awaitable objects and returns a dictionary of results.

    This function is designed to await a mapping of awaitable objects, where each key-value pair represents a unique awaitable. It enables concurrent execution and gathers results into a dictionary.

    Args:
        mapping: A dictionary-like object where keys are of type K and values are awaitable objects of type V.
        return_exceptions: If True, exceptions are returned as results instead of raising them. Defaults to False.
        exclude_if: A callable that takes a result and returns True if the result should be excluded from the final output. Defaults to None.
        tqdm: If True, enables progress reporting using tqdm. Defaults to False.
        **tqdm_kwargs: Additional keyword arguments for tqdm if progress reporting is enabled.

    Example:
        The 'results' dictionary will contain the awaited results, where keys match the keys in the 'mapping' and values contain the results of the corresponding awaitables.

        >>> mapping = {'task1': async_function1(), 'task2': async_function2(), 'task3': async_function3()}
        >>> results = await gather_mapping(mapping)
        >>> results
        {'task1': "result", 'task2': 123, 'task3': None}
    """
    results = {
        k: v
        async for k, v in as_completed_mapping(
            mapping,
            return_exceptions=return_exceptions,
            aiter=True,
            tqdm=tqdm,
            **tqdm_kwargs,
        )
        if exclude_if is None or not exclude_if(v)
    }
    # return data in same order as input mapping
    return {k: results[k] for k in mapping}


_is_mapping = lambda awaitables: len(awaitables) == 1 and isinstance(
    awaitables[0], Mapping
)

__all__ = ["gather", "gather_mapping"]
