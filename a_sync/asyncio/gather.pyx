# cython: boundscheck=False
"""
This module provides an enhanced version of :func:`asyncio.gather`.

This implementation supports two kinds of inputs:
  1. A series of awaitable objects passed as separate positional arguments.
  2. A mapping (i.e. a dict) where each key maps to an awaitable.

In both cases, additional functionality is provided:
  - The progress of the gathered awaitables may be reported using tqdm if enabled.
  - A filtering callable may be passed with the ``exclude_if`` parameter. The callable 
    is applied to each result regardless of whether the input was a mapping or a list.
    Any result for which ``exclude_if(result)`` returns True will be excluded from the final
    output.

See Also:
    :func:`asyncio.gather`
"""

from itertools import filterfalse
from typing import Any, Awaitable, Dict, List, Mapping, Union, overload

from a_sync._typing import *
from a_sync.asyncio cimport as_completed_mapping, cigather

try:
    from tqdm.asyncio import tqdm_asyncio
except ImportError as e:

    class tqdm_asyncio:  # type: ignore [no-redef]
        @staticmethod
        async def gather(*args, **kwargs):
            raise ImportError(
                "You must have tqdm installed in order to use this feature"
            )


Excluder = Callable[[T], bool]


@overload
async def gather(
    awaitables: Mapping[K, Awaitable[V]],
    bint return_exceptions = False,
    exclude_if: Optional[Excluder[V]] = None,
    tqdm: bool = False,
    **tqdm_kwargs: Any,
) -> Dict[K, V]:
    """
    Concurrently awaits a mapping of awaitables and returns a dictionary of results.

    The filtering callable passed via ``exclude_if`` is applied to each awaited result.
    Any result for which ``exclude_if(result)`` returns True is omitted from the final output,
    even when the input is provided as a mapping.

    Args:
        awaitables (Mapping[K, Awaitable[V]]): A mapping object where each key maps to an awaitable.
        return_exceptions (bool, optional): If True, exceptions raised during awaiting are returned as
            results rather than being raised. Defaults to False.
        exclude_if (Optional[Excluder[V]], optional): A callable that takes a single result as an argument.
            If the callable returns True for a given result, that result is excluded from the final output.
            Defaults to None.
        tqdm (bool, optional): If True, enables progress reporting using tqdm. Defaults to False.
        **tqdm_kwargs: Additional keyword arguments passed to tqdm if progress reporting is enabled.

    Examples:
        Awaiting a mapping of awaitables with filtering:

            >>> mapping = {
            ...     'task1': async_function1(),
            ...     'task2': async_function2(),
            ...     'task3': async_function3(),
            ... }
            >>> # Exclude tasks that return None
            >>> results = await gather(mapping, exclude_if=lambda res: res is None)
            >>> results
            {'task1': 'result', 'task3': 123}

    See Also:
        :func:`asyncio.gather`
    """


@overload
async def gather(
    *awaitables: Awaitable[T],
    bint return_exceptions = False,
    exclude_if: Optional[Excluder[T]] = None,
    tqdm: bool = False,
    **tqdm_kwargs: Any,
) -> List[T]:
    """
    Concurrently awaits a sequence of awaitable objects and returns a list of their results.

    The filtering callable passed via ``exclude_if`` is applied to each awaited result.
    Any result for which ``exclude_if(result)`` returns True is excluded from the final output.

    Args:
        *awaitables (Awaitable[T]): Awaitable objects passed as positional arguments.
        return_exceptions (bool, optional): If True, exceptions raised during awaiting are returned as
            results rather than being raised. Defaults to False.
        exclude_if (Optional[Excluder[T]], optional): A callable that takes a single result as input.
            A result is omitted from the final output list if ``exclude_if(result)`` returns True.
            Defaults to None.
        tqdm (bool, optional): If True, enables progress reporting using tqdm. Defaults to False.
        **tqdm_kwargs: Additional keyword arguments passed to tqdm if progress reporting is enabled.

    Examples:
        Awaiting individual awaitables with filtering:

            >>> async def foo(x): return x if x % 2 == 0 else None
            >>> results = await gather(foo(2), foo(3), foo(4), exclude_if=lambda res: res is None)
            >>> # Expected output: [2, 4]
            >>> print(results)
            [2, 4]

    See Also:
        :func:`asyncio.gather`
    """


async def gather(
    *awaitables: Union[Awaitable[T], Mapping[K, Awaitable[V]]],
    bint return_exceptions = False,
    exclude_if: Optional[Excluder[T]] = None,
    tqdm: bool = False,
    **tqdm_kwargs: Any,
) -> Union[List[T], Dict[K, V]]:
    """
    Concurrently awaits a set of awaitables given either as separate arguments or as a mapping,
    and returns the aggregated results.

    This function extends Python's :func:`asyncio.gather` with additional features:

      - It accepts both a series of awaitable objects as positional arguments and
        a mapping (e.g. a dict) of awaitables.
      - It provides progress reporting via tqdm if the ``tqdm`` parameter is True.
      - The filtering callable provided via the ``exclude_if`` parameter is applied
        to every awaited result regardless of the input type. If ``exclude_if(result)``
        returns True for a result, that result is excluded from the final output.
      - If the input is a mapping, the order of keys in the output dictionary is preserved.

    Args:
        *awaitables (Union[Awaitable[T], Mapping[K, Awaitable[V]]]): Either multiple awaitable objects,
            or a single mapping of keys to awaitables.
        return_exceptions (bool, optional): If set to True, exceptions are returned as part of the results
            instead of raising them. Defaults to False.
        exclude_if (Optional[Excluder[T]], optional): A callable that takes the result of an awaited call
            and returns True if that result should be excluded from the final output. This parameter is applied
            uniformly whether the input is provided as positional arguments or as a mapping. Defaults to None.
        tqdm (bool, optional): If True, enables progress reporting using tqdm. Defaults to False.
        **tqdm_kwargs: Additional keyword arguments passed to tqdm if progress reporting is enabled.

    Examples:
        Awaiting individual awaitables with filtering:

            >>> async def process(n):
            ...     return n if n % 2 == 0 else None
            >>> results = await gather(process(1), process(2), process(3), process(4), exclude_if=lambda r: r is None)
            >>> print(results)
            [2, 4]

        Awaiting a mapping of awaitables with filtering:

            >>> async def fetch_data(url):
            ...     # Placeholder for actual asynchronous fetching logic
            ...     return url if "https" in url else None
            >>> urls = {'secure': 'https://secure.com', 'insecure': 'http://insecure.com'}
            >>> results = await gather(urls, exclude_if=lambda r: r is None)
            >>> print(results)
            {'secure': 'https://secure.com'}

    See Also:
        :func:`asyncio.gather`
    """
    if is_mapping := _is_mapping(awaitables):
        results = await gather_mapping(
            awaitables[0],
            return_exceptions=return_exceptions,
            exclude_if=exclude_if,
            tqdm=tqdm,
            **tqdm_kwargs,
        )
    elif tqdm:
        if return_exceptions:
            awaitables = map(_exc_wrap, awaitables)
        results = await tqdm_asyncio.gather(*awaitables, **tqdm_kwargs)
    else:
        results = await cigather(awaitables, return_exceptions=return_exceptions)

    if exclude_if and not is_mapping:
        return list(filterfalse(exclude_if, results))

    return results


async def gather_mapping(
    mapping: Mapping[K, Awaitable[V]],
    bint return_exceptions = False,
    exclude_if: Optional[Excluder[V]] = None,
    tqdm: bool = False,
    **tqdm_kwargs: Any,
) -> Dict[K, V]:
    """
    Concurrently awaits a mapping of awaitable objects and returns a dictionary of results.

    In this function, the filtering callable provided as ``exclude_if`` is applied to each awaited result;
    if ``exclude_if(result)`` returns True, then that key-result pair is omitted from the final dictionary.
    This behavior applies uniformly regardless of the input type.

    Args:
        mapping (Mapping[K, Awaitable[V]]): A mapping where keys are associated with awaitable objects.
        return_exceptions (bool, optional): If True, any exceptions raised during the awaiting process are returned
            as their corresponding values rather than being raised. Defaults to False.
        exclude_if (Optional[Excluder[V]], optional): A callable that receives the result of each awaitable. If
            the callable returns True for a particular result, that result is excluded from the output.
            Defaults to None.
        tqdm (bool, optional): If True, enables progress reporting using tqdm. Defaults to False.
        **tqdm_kwargs: Additional keyword arguments passed to tqdm when progress reporting is enabled.

    Examples:
        Awaiting a mapping of awaitables with filtering:

            >>> async def compute(x):
            ...     return x * 2
            >>> mapping = {
            ...     'first': compute(10),
            ...     'second': compute(20),
            ...     'third': compute(0),
            ... }
            >>> # Exclude results that are zero.
            >>> results = await gather_mapping(mapping, exclude_if=lambda r: r == 0)
            >>> print(results)
            {'first': 20, 'second': 40}

    See Also:
        :func:`asyncio.gather`
    """
    results = {
        k: v
        async for k, v in as_completed_mapping(
            mapping=mapping,
            timeout=0,
            return_exceptions=return_exceptions,
            aiter=True,
            tqdm=tqdm,
            tqdm_kwargs=tqdm_kwargs,
        )
        if exclude_if is None or not exclude_if(v)
    }
    # Return data in the same order as the input mapping
    return {k: results[k] for k in mapping}


def cgather(*coros_or_futures: Awaitable[T], bint return_exceptions = False) -> Awaitable[List[T]]:
    """`asyncio.gather` implemented in C."""
    return cigather(coros_or_futures, return_exceptions=return_exceptions)


cdef inline bint _is_mapping(tuple awaitables):
    return len(awaitables) == 1 and isinstance(awaitables[0], Mapping)


async def _exc_wrap(awaitable: Awaitable[T]) -> Union[T, Exception]:
    """
    Wrap an awaitable to catch exceptions and return them as the result.

    Args:
        awaitable: An awaitable object which may raise an exception during awaiting.

    Examples:
        Suppose a coroutine might raise an exception; wrapping it will yield either its result or the exception:

            >>> result = await _exc_wrap(might_fail())
            >>> if isinstance(result, Exception):
            ...     print("An error occurred:", result)
            ... else:
            ...     print("Success:", result)

    See Also:
        :func:`asyncio.gather`
    """
    try:
        return await awaitable
    except Exception as e:
        return e