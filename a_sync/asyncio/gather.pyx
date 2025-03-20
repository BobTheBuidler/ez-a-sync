# cython: boundscheck=False
"""
This module provides an enhanced version of :func:`asyncio.gather`.
"""
from asyncio import CancelledError, gather as aiogather, _ensure_future
from asyncio.events import _get_event_loop
from asyncio.futures import _get_loop
from asyncio.tasks import _GatheringFuture
from itertools import filterfalse
from typing import Any, Awaitable, Dict, List, Mapping, Union, overload

from a_sync._typing import *
from a_sync.asyncio.as_completed cimport as_completed_mapping

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
    return_exceptions: bool = False,
    exclude_if: Optional[Excluder[V]] = None,
    tqdm: bool = False,
    **tqdm_kwargs: Any,
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
    **tqdm_kwargs: Any,
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


async def gather(
    *awaitables: Union[Awaitable[T], Mapping[K, Awaitable[V]]],
    return_exceptions: bool = False,
    exclude_if: Optional[Excluder[T]] = None,
    tqdm: bool = False,
    **tqdm_kwargs: Any,
) -> Union[List[T], Dict[K, V]]:
    """
    Concurrently awaits a list of awaitable objects or a k:v mapping of awaitables, and returns the results.

    This function extends Python's :func:`asyncio.gather`, providing additional features for handling either individual
    awaitable objects or a single mapping of awaitables.

    Differences from :func:`asyncio.gather`:
    - Uses type hints for use with static type checkers.
    - Supports gathering either individual awaitables or a k:v mapping of awaitables.
    - Provides progress reporting using tqdm if 'tqdm' is set to True.
    - Allows exclusion of results based on a condition using the 'exclude_if' parameter. Note: This is only applied when the input is not a mapping.

    Args:
        *awaitables (Union[Awaitable[T], Mapping[K, Awaitable[V]]]): The awaitables to await concurrently. It can be a list of individual awaitables or a single mapping of awaitables.
        return_exceptions (bool, optional): If True, exceptions are returned as results instead of raising them. Defaults to False.
        exclude_if (Optional[Excluder[T]], optional): A callable that takes a result and returns True if the result should be excluded from the final output. Defaults to None. Note: This is only applied when the input is not a mapping.
        tqdm (bool, optional): If True, enables progress reporting using tqdm. Defaults to False.
        **tqdm_kwargs: Additional keyword arguments for tqdm if progress reporting is enabled.

    Examples:
        Awaiting individual awaitables:

        >>> results = await gather(thing1(), thing2())
        >>> results
        ['result', 123]

        Awaiting a mapping of awaitables:

        >>> mapping = {'key1': thing1(), 'key2': thing2()}
        >>> results = await gather(mapping)
        >>> results
        {'key1': 'result', 'key2': 123}

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
        results = await tqdm_asyncio.gather(
            *(map(_exc_wrap, awaitables) if return_exceptions else awaitables),
            **tqdm_kwargs,
        )
    else:
        results = await igather(awaitables, return_exceptions=return_exceptions)

    if exclude_if and not is_mapping:
        return list(filterfalse(exclude_if, results))

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
        mapping (Mapping[K, Awaitable[V]]): A dictionary-like object where keys are of type K and values are awaitable objects of type V.
        return_exceptions (bool, optional): If True, exceptions are returned as results instead of raising them. Defaults to False.
        exclude_if (Optional[Excluder[V]], optional): A callable that takes a result and returns True if the result should be excluded from the final output. Defaults to None. Note: This is not applied when the input is a mapping.
        tqdm (bool, optional): If True, enables progress reporting using tqdm. Defaults to False.
        **tqdm_kwargs: Additional keyword arguments for tqdm if progress reporting is enabled.

    Example:
        The 'results' dictionary will contain the awaited results, where keys match the keys in the 'mapping' and values contain the results of the corresponding awaitables.

        >>> mapping = {'task1': async_function1(), 'task2': async_function2(), 'task3': async_function3()}
        >>> results = await gather_mapping(mapping)
        >>> results
        {'task1': "result", 'task2': 123, 'task3': None}

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
    # return data in same order as input mapping
    return {k: results[k] for k in mapping}


cdef inline bint _is_mapping(tuple awaitables):
    return len(awaitables) == 1 and isinstance(awaitables[0], Mapping)


async def _exc_wrap(awaitable: Awaitable[T]) -> Union[T, Exception]:
    """Wraps an awaitable to catch exceptions and return them instead of raising.

    Args:
        awaitable: The awaitable to wrap.

    Returns:
        The result of the awaitable or the exception if one is raised.
    """
    try:
        return await awaitable
    except Exception as e:
        return e
    

def cgather(*coros_or_futures, bint return_exceptions=False) -> Awaitable[List[T]]:
    return igather(coros_or_futures, return_exceptions=return_exceptions)

cpdef inline object igather(coros_or_futures: Iterator[Awaitable[T]], bint return_exceptions=False):
    """A clone of asyncio.gather that takes a single iterator of coroutines instead of an unpacked tuple."""
    return _igather(coros_or_futures, return_exceptions=return_exceptions)

cdef object _igather(coros_or_futures: Iterator[Awaitable[T]], bint return_exceptions=False):
    # NOTE: closures inside cpdef functions not yet supported, so we have this cdef helper
    cdef long long nfuts, nfinished
    cdef dict arg_to_fut = {}
    cdef list children = []
    loop = None
    for arg in coros_or_futures:
        if arg not in arg_to_fut:
            fut = _ensure_future(arg, loop=loop)
            if loop is None:
                loop = _get_loop(fut)
            if fut is not arg:
                # 'arg' was not a Future, therefore, 'fut' is a new
                # Future created specifically for 'arg'.  Since the caller
                # can't control it, disable the "destroy pending task"
                # warning.
                fut._log_destroy_pending = False

            nfuts += 1
            arg_to_fut[arg] = fut

        else:
            # There's a duplicate Future object in coros_or_futures.
            fut = arg_to_fut[arg]

        children.append(fut)

    if not children:
        loop = _get_event_loop()
        return _get_noop_future_for_loop(loop)
    
    nfuts = len(arg_to_fut)
    nfinished = 0
    outer = None  # bpo-46672
    
    def _done_callback(fut):
        nonlocal nfinished
        nfinished += 1

        if outer is None or outer.done():
            if not fut.cancelled():
                # Mark exception retrieved.
                fut.exception()
            return

        if not return_exceptions:
            if fut.cancelled():
                # Check if 'fut' is cancelled first, as
                # 'fut.exception()' will *raise* a CancelledError
                # instead of returning it.
                exc = fut._make_cancelled_error()
                outer.set_exception(exc)
                return
            else:
                exc = fut.exception()
                if exc is not None:
                    outer.set_exception(exc)
                    return

        if nfinished == nfuts:
            # All futures are done; create a list of results
            # and set it to the 'outer' future.

            if outer._cancel_requested:
                # If gather is being cancelled we must propagate the
                # cancellation regardless of *return_exceptions* argument.
                # See issue 32684.
                exc = fut._make_cancelled_error()
                outer.set_exception(exc)
            else:
                results = list(map(_get_result_or_exc, children))
                outer.set_result(results)

    for fut in arg_to_fut.values():
        fut.add_done_callback(_done_callback)
    


    outer = _GatheringFuture(children, loop=loop)
    return outer


cdef public dict[object, object] _noop_futures = {}

def _get_noop_future_for_loop(loop):
    fut = _noop_futures.get(loop)
    if fut is None:
        fut = _noop_futures[loop] = loop.create_future()
        fut.set_result([])
    return fut

cdef object _get_result_or_exc(fut: Future):
    if fut.cancelled():
        # Check if 'fut' is cancelled first, as 'fut.exception()'
        # will *raise* a CancelledError instead of returning it.
        # Also, since we're adding the exception return value
        # to 'results' instead of raising it, don't bother
        # setting __context__.  This also lets us preserve
        # calling '_make_cancelled_error()' at most once.
        return CancelledError(
            '' if fut._cancel_message is None else fut._cancel_message
        )
    res = fut.exception()
    if res is None:
        return fut.result()
    return res