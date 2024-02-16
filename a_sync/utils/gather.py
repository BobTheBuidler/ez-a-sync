
import asyncio
from typing import (Any, Awaitable, Dict, List, Mapping, TypeVar, Union,
                    overload)

try:
    from tqdm.asyncio import tqdm_asyncio
except ImportError as e:
    class tqdm_asyncio:  # type: ignore [no-redef]
        async def gather(*args, **kwargs):
            raise ImportError("You must have tqdm installed in order to use this feature")

from a_sync._typing import *
from a_sync.utils.as_completed import as_completed_mapping


Excluder = Callable[[T], bool]

@overload
async def gather(
    *awaitables: Mapping[K, Awaitable[V]], 
    return_exceptions: bool = False, 
    exclude_if: Optional[Excluder[T]] = None, 
    tqdm: bool = False, 
    **tqdm_kwargs: Any,
) -> Dict[K, V]:
    ...
@overload
async def gather(
    *awaitables: Awaitable[T], 
    return_exceptions: bool = False, 
    exclude_if: Optional[Excluder[T]] = None,
    tqdm: bool = False,
    **tqdm_kwargs: Any,
) -> List[T]:
    ...
async def gather(
    *awaitables: Union[Awaitable[T], Mapping[K, Awaitable[V]]], 
    return_exceptions: bool = False, 
    exclude_if: Optional[Excluder[T]] = None, 
    tqdm: bool = False, 
    **tqdm_kwargs: Any,
) -> Union[List[T], Dict[K, V]]:
    """
    Concurrently awaits a list of awaitable objects or mappings of awaitables and returns the results.

    This function extends Python's asyncio.gather, providing additional features for mixed use cases of individual awaitable objects and mappings of awaitables.

    Differences from asyncio.gather:
    - Uses type hints for use with static type checkers.
    - Supports gathering either individual awaitables or a k:v mapping of awaitables.
    - Provides progress reporting using tqdm if 'tqdm' is set to True.
    
    Args:
        *awaitables (Union[Awaitable[T], Mapping[K, Awaitable[V]]]): The awaitables to await concurrently. It can be a single awaitable or a mapping of awaitables.
        return_exceptions (bool, optional): If True, exceptions are returned as results instead of raising them. Defaults to False.
        tqdm (bool, optional): If True, enables progress reporting using tqdm. Defaults to False.
        **tqdm_kwargs: Additional keyword arguments for tqdm if progress reporting is enabled.

    Returns:
        Union[List[T], Dict[K, V]]: A list of results when awaiting individual awaitables or a dictionary of results when awaiting mappings.

    Examples:
        Awaiting individual awaitables:
        results will be a list containing the result of each awaitable in sequential order
        ```
        results = await gather(thing1(), thing2())
        ```

        Awaiting mappings of awaitables
        results will be a dictionary with 'key1' mapped to the result of thing1() and 'key2' mapped to the result of thing2.
        ```
        mapping = {'key1': thing1(), 'key2': thing2()}
        results = await gather(mapping)
        ```
    """
    results = await (
        gather_mapping(awaitables[0], return_exceptions=return_exceptions, tqdm=tqdm, **tqdm_kwargs) if _is_mapping(awaitables)
        else tqdm_asyncio.gather(*awaitables, return_exceptions=return_exceptions, **tqdm_kwargs) if tqdm
        else asyncio.gather(*awaitables, return_exceptions=return_exceptions)  # type: ignore [arg-type]
    )
    if exclude_if:
        results = [r for r in results if not exclude_if(r)]
    return results
    
async def gather_mapping(mapping: Mapping[K, Awaitable[V]], return_exceptions: bool = False, tqdm: bool = False, **tqdm_kwargs: Any) -> Dict[K, V]:
    """
    Concurrently awaits a mapping of awaitable objects and returns a dictionary of results.

    This function is designed to await a mapping of awaitable objects, where each key-value pair represents a unique awaitable. It enables concurrent execution and gathers results into a dictionary.

    Args:
        mapping (Mapping[K, Awaitable[V]]): A dictionary-like object where keys are of type K and values are awaitable objects of type V.
        return_exceptions (bool, optional): If True, exceptions are returned as results instead of raising them. Defaults to False.
        tqdm (bool, optional): If True, enables progress reporting using tqdm. Defaults to False.
        **tqdm_kwargs: Additional keyword arguments for tqdm if progress reporting is enabled.

    Returns:
        Dict[K, V]: A dictionary with keys corresponding to the keys of the input mapping and values containing the results of the corresponding awaitables.

    Example:
        The 'results' dictionary will contain the awaited results, where keys match the keys in the 'mapping' and values contain the results of the corresponding awaitables.
        ```
        mapping = {'task1': async_function1(), 'task2': async_function2(), 'task3': async_function3()}

        results = await gather_mapping(mapping)
        ```
    """
    results = {k: v async for k, v in as_completed_mapping(mapping, return_exceptions=return_exceptions, aiter=True, tqdm=tqdm, **tqdm_kwargs)}
    return {k: results[k] for k in mapping.keys()}  # return data in same order as input mapping

_is_mapping = lambda awaitables: len(awaitables) == 1 and isinstance(awaitables[0], Mapping)
