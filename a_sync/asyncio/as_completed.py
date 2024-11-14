"""
This module extends Python's :func:`asyncio.as_completed` with additional functionality.
"""

import asyncio

try:
    from tqdm.asyncio import tqdm_asyncio
except ImportError as e:

    class tqdm_asyncio:  # type: ignore [no-redef]
        @staticmethod
        def as_completed(*args, **kwargs):
            raise ImportError("You must have tqdm installed to use this feature")


from a_sync._typing import *
from a_sync.iter import ASyncIterator


@overload
def as_completed(
    fs: Iterable[Awaitable[T]],
    *,
    timeout: Optional[float] = None,
    return_exceptions: bool = False,
    aiter: Literal[False] = False,
    tqdm: bool = False,
    **tqdm_kwargs: Any
) -> Iterator[Coroutine[Any, Any, T]]: ...
@overload
def as_completed(
    fs: Iterable[Awaitable[T]],
    *,
    timeout: Optional[float] = None,
    return_exceptions: bool = False,
    aiter: Literal[True] = True,
    tqdm: bool = False,
    **tqdm_kwargs: Any
) -> ASyncIterator[T]: ...
@overload
def as_completed(
    fs: Mapping[K, Awaitable[V]],
    *,
    timeout: Optional[float] = None,
    return_exceptions: bool = False,
    aiter: Literal[False] = False,
    tqdm: bool = False,
    **tqdm_kwargs: Any
) -> Iterator[Coroutine[Any, Any, Tuple[K, V]]]: ...
@overload
def as_completed(
    fs: Mapping[K, Awaitable[V]],
    *,
    timeout: Optional[float] = None,
    return_exceptions: bool = False,
    aiter: Literal[True] = True,
    tqdm: bool = False,
    **tqdm_kwargs: Any
) -> ASyncIterator[Tuple[K, V]]: ...
def as_completed(
    fs,
    *,
    timeout: Optional[float] = None,
    return_exceptions: bool = False,
    aiter: bool = False,
    tqdm: bool = False,
    **tqdm_kwargs: Any
):
    """
    Concurrently awaits a list of awaitable objects or mappings of awaitables and returns an iterator of results.

    This function extends Python's :func:`asyncio.as_completed`, providing additional features for mixed use cases of individual awaitable objects and mappings of awaitables.

    Differences from :func:`asyncio.as_completed`:
    - Uses type hints for use with static type checkers.
    - Supports either individual awaitables or a k:v mapping of awaitables.
    - Can be used as an async iterator which yields the result values using :class:`ASyncIterator`.
    - Provides progress reporting using :mod:`tqdm` if 'tqdm' is set to True.

    Note:
        The `return_exceptions` parameter is used to wrap awaitables with exceptions if set to True, allowing exceptions to be returned as results instead of being raised.

    Args:
        fs: The awaitables to await concurrently. It can be a list of individual awaitables or a mapping of awaitables.
        timeout: The maximum time, in seconds, to wait for the completion of awaitables. Defaults to None (no timeout).
        return_exceptions: If True, exceptions are wrapped and returned as results instead of raising them. Defaults to False.
        aiter: If True, returns an async iterator of results using :class:`ASyncIterator`. Defaults to False.
        tqdm: If True, enables progress reporting using :mod:`tqdm`. Defaults to False.
        **tqdm_kwargs: Additional keyword arguments for :mod:`tqdm` if progress reporting is enabled.

    Examples:
        Awaiting individual awaitables:

        >>> awaitables = [async_function1(), async_function2()]
        >>> for coro in as_completed(awaitables):
        ...     val = await coro
        ...     ...

        >>> async for val in as_completed(awaitables, aiter=True):
        ...     ...

        Awaiting mappings of awaitables:

        >>> mapping = {'key1': async_function1(), 'key2': async_function2()}
        >>> for coro in as_completed(mapping):
        ...     k, v = await coro
        ...     ...

        >>> async for k, v in as_completed(mapping, aiter=True):
        ...     ...

    See Also:
        - :func:`asyncio.as_completed`
        - :class:`ASyncIterator`
    """
    if isinstance(fs, Mapping):
        return as_completed_mapping(
            fs,
            timeout=timeout,
            return_exceptions=return_exceptions,
            aiter=aiter,
            tqdm=tqdm,
            **tqdm_kwargs
        )
    if return_exceptions:
        fs = [_exc_wrap(f) for f in fs]
    return (
        ASyncIterator(
            __yield_as_completed(fs, timeout=timeout, tqdm=tqdm, **tqdm_kwargs)
        )
        if aiter
        else (
            tqdm_asyncio.as_completed(fs, timeout=timeout, **tqdm_kwargs)
            if tqdm
            else asyncio.as_completed(fs, timeout=timeout)
        )
    )


@overload
def as_completed_mapping(
    mapping: Mapping[K, Awaitable[V]],
    *,
    timeout: Optional[float] = None,
    return_exceptions: bool = False,
    aiter: Literal[True] = True,
    tqdm: bool = False,
    **tqdm_kwargs: Any
) -> ASyncIterator[Tuple[K, V]]: ...
@overload
def as_completed_mapping(
    mapping: Mapping[K, Awaitable[V]],
    *,
    timeout: Optional[float] = None,
    return_exceptions: bool = False,
    aiter: Literal[False] = False,
    tqdm: bool = False,
    **tqdm_kwargs: Any
) -> Iterator[Coroutine[Any, Any, Tuple[K, V]]]: ...
def as_completed_mapping(
    mapping: Mapping[K, Awaitable[V]],
    *,
    timeout: Optional[float] = None,
    return_exceptions: bool = False,
    aiter: bool = False,
    tqdm: bool = False,
    **tqdm_kwargs: Any
) -> Union[Iterator[Coroutine[Any, Any, Tuple[K, V]]], ASyncIterator[Tuple[K, V]]]:
    """
    Concurrently awaits a mapping of awaitable objects and returns an iterator or async iterator of results.

    This function is designed to await a mapping of awaitable objects, where each key-value pair represents a unique awaitable. It enables concurrent execution and gathers results into an iterator or an async iterator.

    Args:
        mapping: A dictionary-like object where keys are of type K and values are awaitable objects of type V.
        timeout: The maximum time, in seconds, to wait for the completion of awaitables. Defaults to None (no timeout).
        return_exceptions: If True, exceptions are wrapped and returned as results instead of raising them. Defaults to False.
        aiter: If True, returns an async iterator of results using :class:`ASyncIterator`. Defaults to False.
        tqdm: If True, enables progress reporting using :mod:`tqdm`. Defaults to False.
        **tqdm_kwargs: Additional keyword arguments for :mod:`tqdm` if progress reporting is enabled.

    Example:
        >>> mapping = {'key1': async_function1(), 'key2': async_function2()}
        >>> for coro in as_completed_mapping(mapping):
        ...     k, v = await coro
        ...     ...

        >>> async for k, v in as_completed_mapping(mapping, aiter=True):
        ...     ...

    See Also:
        - :func:`as_completed`
        - :class:`ASyncIterator`
    """
    return as_completed(
        [
            __mapping_wrap(k, v, return_exceptions=return_exceptions)
            for k, v in mapping.items()
        ],
        timeout=timeout,
        aiter=aiter,
        tqdm=tqdm,
        **tqdm_kwargs
    )


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


async def __yield_as_completed(
    futs: Iterable[Awaitable[T]],
    *,
    timeout: Optional[float] = None,
    return_exceptions: bool = False,
    tqdm: bool = False,
    **tqdm_kwargs: Any
) -> AsyncIterator[T]:
    """Yields results from awaitables as they complete.

    Args:
        futs: The awaitables to await.
        timeout: The maximum time, in seconds, to wait for the completion of awaitables. Defaults to None (no timeout).
        return_exceptions: If True, exceptions are wrapped and returned as results instead of raising them. Defaults to False.
        tqdm: If True, enables progress reporting using :mod:`tqdm`. Defaults to False.
        **tqdm_kwargs: Additional keyword arguments for :mod:`tqdm` if progress reporting is enabled.
    """
    for fut in as_completed(
        futs,
        timeout=timeout,
        return_exceptions=return_exceptions,
        tqdm=tqdm,
        **tqdm_kwargs
    ):
        yield await fut


@overload
async def __mapping_wrap(
    k: K, v: Awaitable[V], return_exceptions: Literal[True] = True
) -> Union[V, Exception]: ...
@overload
async def __mapping_wrap(
    k: K, v: Awaitable[V], return_exceptions: Literal[False] = False
) -> V: ...
async def __mapping_wrap(
    k: K, v: Awaitable[V], return_exceptions: bool = False
) -> Union[V, Exception]:
    """Wraps a key-value pair of awaitable to catch exceptions and return them with the key.

    Args:
        k: The key associated with the awaitable.
        v: The awaitable to wrap.
        return_exceptions: If True, exceptions are wrapped and returned as results instead of raising them. Defaults to False.

    Returns:
        A tuple of the key and the result of the awaitable or the exception if one is raised.
    """
    try:
        return k, await v
    except Exception as e:
        if return_exceptions:
            return k, e
        raise


__all__ = ["as_completed", "as_completed_mapping"]
